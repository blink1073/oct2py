import os
import subprocess
import atexit
import re
import pdb
import numpy as np
try:
    import h5py
except:
    'Please install h5py from "http://code.google.com/p/h5py/downloads/list"'
    raise

# TODO: documentation, run against m-files, setup.py, add to bitbucket, send link to Scipy
#       future enhancements: add compability check using octave library
#                             add cell array write capability
# NOTE: talk about the limitations of Octave up front - nested functions class


def close(handle):
    """ Closes an octave session

    Called when the octave object is deleted or at program exit
    """
    try:
        handle.stdin.write('exit')
    except:
        pass

class OctaveError(Exception):
    """ Called when we can't open Octave or octave throws an error """
    pass

class OctaveStruct(dict):
    ''' Octave style struct.  
    
    Supports dictionary and attribute style access.
    
    a = OctaveStruct()
    a.b = 'spam'  # a["b"] == 'spam'
    a.c["d"] = 'eggs'  # a.c.d == 'eggs'
    '''
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            self[attr] = OctaveStruct()
            return self[attr]
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    

class OctaveH5Read(object):
    
    def __init__(self, out_file):
        self.out_file = out_file
        
    def setup(self, nout, names=None):
        ''' Generate the argout list and the Octave save command '''
        argout_list = []
        ascii_code = 97
        for i in range(nout):
            if names:
                argout_list.append(names.pop(0))
            else:
                argout_list.append("%s__" % chr(ascii_code))
            ascii_code += 1
        save_line = 'save "-hdf5" "%s" "%s"' % (self.out_file, 
                                                '" "'.join(argout_list))
        return argout_list, save_line
        
    def extract_file(self, argout_list):
        ''' Extract the variables in argout_list from the HDF file '''
        fid = h5py.File(self.out_file)
        outputs = []
        for arg in argout_list:
           try:
               val = self._getval(fid[arg])
           except:
               val = self._getvals(fid[arg]['value'])
           outputs.append(val)
        fid.close()
        os.remove(self.out_file)
        if len(outputs) > 1:
            return tuple(outputs)
        else:
            return outputs[0]

    def _getval(self, group):
        ''' Handle variable types that do not translate directly
        '''
        type_ = group['type'].value
        val = group['value'].value
        # strings come in as byte arrays
        if type_ == 'sq_string' or type_ == 'string':
            val = [chr(char) for char in val]
            val = ''.join(val)
        # complex scalars come in as tuples
        elif type_ == 'complex scalar':
            val = val[0] + val[1] * 1j
        # complex matrices come in as ndarrays with real and imag parts
        elif type_ == 'complex matrix':
            temp = [x + y * 1j for x, y in val.ravel()]
            val = np.array(temp).reshape(val.shape)
        # Matlab reads the data in Fortran order, not 'C' order
        if isinstance(val, np.ndarray):
            val = val.T
        return val
    
    def _getvals(self, group):
       ''' Extract a nested struct / cell array from the HDF file

       Structs become dictionaries, cell arrays become lists
       '''
       data = OctaveStruct()
       try:
           for key in group.keys():
               if key ==  'dims':
                   data['dims'] = group[key].value
               elif isinstance(group[key]['value'], h5py.Group):
                   if key.startswith('_'):
                       data[int(key[1:])] = self._getvals(group[key]['value'])
                   else:
                       data[key] = self._getvals(group[key]['value'])
               else:
                   val = self._getval(group[key])
                   if key.startswith('_'):
                       key = int(key[1:])
                   data[key] = val
       except AttributeError:
           # handle top-level cell arrays
           temp = [chr(item) for item in group.value.ravel()]
           temp = np.array(temp).reshape(group.value.shape)
           data = []
           for row in range(temp.shape[1]):
               data.append(''.join(temp[:, row]))
       # handle nested cell arrays
       if 'dims' in data:
           data = self._extract_cell_array(data)
       return data
       
    def _extract_cell_array(self, data):
        ''' Extract a nested cell array from a dictionary  '''
        dims = data['dims']
        # only worry about 1-d and 2-d
        if len(dims) == 2:
           # singleton
           if dims[0] == 1 and dims[1] == 1:
               data = data[0]
           # array
           elif dims[0] == 1 or dims[1] == 1:
               del data['dims']
               data = [data[key] for key in sorted(data.keys())]
           # matrix
           else:
               temp = []
               for row in range(dims[0]):
                   start = row * dims[1]
                   stop = (row + 1) * dims[1]
                   temp.append([data[key] for key in range(start, stop)])
               data = temp
        return data
        
class OctaveH5Write(object):
    
    def __init__(self, in_file):
        self.in_file = in_file
        
    def create_file(self, inputs, names=None):
        ''' Create an HDF file, loading the input variables 
        
        If names are given, use those, otherwise use dummies
        '''
        fid = h5py.File(self.in_file, "w")
        # create a dummy list of var names ("A", "B", "C" ...)
        # use ascii char codes so we can increment
        argin_list = []
        ascii_code = 65
        for var in inputs:
            if names:
                argin_list.append(names.pop(0))
            else:
                argin_list.append("%s__" % chr(ascii_code))
            #pdb.set_trace()
            # for structs - recursively add the elements
            if isinstance(var, dict):
                sub = fid.create_group(argin_list[-1])
                self._putvals(sub, var)
            else:
                self._putval(fid, argin_list[-1], var)
            ascii_code += 1
        fid.close()
        load_line = 'load "-hdf5" "%s" "%s"' % (self.in_file,
                                                '" "'.join(argin_list))
        return argin_list, load_line
        
    def _putvals(self, group, dict_):
        ''' Put a nested dict into the HDF file as a struct
        '''
        for key in dict_.keys():
            if isinstance(dict_[key], dict):
                sub = group.create_group(key)
                self._putvals(sub, dict_[key])
            else:
                self._putval(group, key, dict_[key])
            
    def _putval(self, group, name, data):
        ''' Handle variable types that do not translate directly
        '''
        # the last char is stripped off in transit
        if isinstance(data, str):
            data += '_'
        # lists get mangled unless you make them an ndarrays
        # XXX they will still get mangled for cell arrays 
        #      (vectors work though)
        elif isinstance(data, list):
            data = np.array(data)
            # pad the strings here too
            if '|S' in data.dtype.str:
                if len(data.shape) > 1:
                    raise OctaveError('Cannot pass nested lists:\n%s' % data)
                nchars = int(data.dtype.str[2:])
                data = data.astype(np.dtype('|S%s' % (nchars + 1)))
        # matlab expects a specific array type for complex nums
        elif isinstance(data, complex):
            data = np.array((data.real, data.imag), 
                           dtype=np.dtype([('real', '<f8'), 
                                           ('imag', '<f8')]))
        if isinstance(data, np.ndarray):
            if data.dtype == np.dtype('complex128'):
                temp = [(item.real, item.imag) for item in data.ravel()]
                temp = np.array(temp, dtype=np.dtype([('real', '<f8'), 
                                           ('imag', '<f8')]))
                data = temp.reshape(data.shape)
            # Matlab reads the data in Fortran order, not 'C' order
            data = data.T
        group.create_dataset(name, data=data)


class Octave(object):

    def __init__(self):
        ''' Start Octave and create our HDF helpers
        '''
        self._session = self._open()
        self._reader = OctaveH5Read('__output__.hdf')
        self._writer = OctaveH5Write('__input__.hdf')
        
    def _open(self):
        ''' Start an octave session in a subprocess

        Attempts to call "octave" or raise an error
         -q is quiet startup, --braindead is Matlab compatibilty mode
        '''
        session = None
        try:
            cmd = 'octave -q --braindead'
            session = subprocess.Popen(cmd, shell=True,
                                     stderr=subprocess.STDOUT,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)
        except WindowsError:
            from glob import glob
            octave_path = glob('c:/Octave/*/bin/octave.exe')[0]
            if not os.path.exists(octave_path):
                msg = ('Please install Octave at "c:/Octave" '
                         '  or put it in your path:\n'
                         'setx PATH "%PATH%;<path-to-octave-bin-dir>"')
                raise OctaveError(msg)
            else:
                cmd = 'octave -q --braindead'
                session = subprocess.Popen(cmd, shell=True,
                                     stderr=subprocess.STDOUT,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)
        except OSError:
            raise OctaveError('Please put the Octave executable in your PATH')
        atexit.register(lambda handle=session: close(handle))
        return session
        
    def run(self, script, **kwargs):
        ''' Runs a script or an m-file
        
        Keywords implemented:
            verbose : If true, all m-file prints will be displayed
        '''
        # don't return a value from a script
        kwargs['nout']  = 0
        # this line is needed to force the plot to display
        for cmd in ['gplot', 'plot', 'bar', 'contour', 'hist', 'loglog', 
                    'polar', 'semilogx', 'stairs', 'gsplot', 'mesh', 
                    'meshdom']:
            if cmd in script:
                script += ';print -deps foo.eps;'
                break
        return self.call(script, **kwargs)
        
    def call(self, func, *inputs, **kwargs):
        """  Calls an M file using Octave
        If inputs are provided, they are passed to octave
           Pass in the inputs as unnamed parameters after the function name
        If verbose is in the keyword args, the response from octave
           will be printed

        Uses HDF5 files to pass data between Octave and Numpy - requires h5py

        Notes:
        The function must either exist as an m-file in this directory or
        on Octave's path.

        The first command will take about 0.5s for Octave to load up.
        The subsequent commands will be much faster.
        
        Plotting commands within an m file do not work 
        Unless you add this after every plot line: print -deps foo.eps
        The following plots are supported by GNU Octave:
        ['gplot', 'plot', 'bar', 'contour', 'hist', 'loglog', 
         'polar', 'semilogx', 'stairs', 'gsplot', 'mesh', 'meshdom']

        Usage:

          >> import octave
          >> x = 2
          >> y = 1
          >> a = octave.call('zeros', x, y, verbose=True)

          array([[ 0.,  0.]])
          >> print a
          [[ 0.  0.]]
        """
        verbose = kwargs.get('verbose', False)
        nout = kwargs.get('nout', self._get_nout())

        # Don't call if octave isn't running (bad path or an error)
        if not self._session:
            raise OctaveError('Octave unavailable')

        # handle references to script names - and paths to them
        if func.endswith('.m'):
            if os.path.dirname(func):
                self.addpath(os.path.dirname(func))
                func = os.path.basename(func)
            func = func[:-2]
        
        # these three lines will form the commands sent to Octave
        # load("-hdf5", "infile", "invar1", ...)
        # [a, b, c] = foo(A, B, C)
        # save("-hdf5", "outfile", "outvar1", ...)
        load_line, call_line, save_line = '', '', ''

        if nout:
            # create a dummy list of var names ("a", "b", "c", ...)
            # use ascii char codes so we can increment
            argout_list, save_line = self._reader.setup(nout)
            call_line = '[%s] = ' %  (', '.join(argout_list))
        if inputs:
            argin_list, load_line = self._writer.create_file(inputs)
            call_line += '%s(%s);' % (func, ', '.join(argin_list))  
        elif nout:
            # call foo() - no arguments
            call_line += '%s();' % func
        else:
            # run foo
            call_line += '%s;' % func
        # A special command is needed to force the plot to display
        if func in ['gplot', 'plot', 'bar', 'contour', 'hist', 'loglog', 
                    'polar', 'semilogx', 'semilogy', 'stairs', 'gsplot', 
                    'mesh', 'meshdom', 'meshc', 'surf', 'plot3', 'meshz', 
                    'surfc', 'surfl', 'surfnorm', 'diffuse', 'specular', 
                    'ribbon', 'scatter3']:
            call_line += ';print -deps foo.eps;'

        # create the command and execute in octave
        cmd = [load_line, call_line, save_line]
        resp = self._eval(cmd, verbose=verbose)
        
        if nout:
            return self._reader.extract_file(argout_list)
        else:
            return resp
    
    def put(self, name, var):
        if isinstance(name, str):
            var = [var]
            name = [name]
        argin_list, load_line = self._writer.create_file(var, name)
        return self._eval(load_line)
        
    def get(self, var):
        if isinstance(var, str):
            var = [var]
        argout_list, save_line = self._reader.setup(1, var)
        self._eval(save_line)
        return self._reader.extract_file(argout_list)
        
    def lookfor(self, string):
        ''' Calls the octave "lookfor" command, with the -all switch '''
        return self.run('lookfor -all %s' % string, verbose=True)

    def _eval(self, cmds, verbose=True):
        resp = []
        # use ascii code 201 to signal an error and 200 
        # to signal action complete
        #pdb.set_trace()
        if isinstance(cmds, str):
            cmds = [cmds]
        lines = ['try', '\n'.join(cmds), 'disp(char(200))',
                 'catch', 'disp(lasterr())', 'disp(char(201))', 
                 'end', '']
        eval_ = '\n'.join(lines)
        self._session.stdin.write(eval_)
        while 1:
            line = self._session.stdout.readline().rstrip()
            #import pdb; pdb.set_trace()
            if line == chr(200):
                break
            elif line == chr(201):
                msg = '"""\n%s\n"""\n%s' % ('\n'.join(cmds), '\n'.join(resp))
                raise OctaveError(msg)
            elif verbose:
                print line
            resp.append(line)
        return '\n'.join(resp)
        
    def _get_nout(self):
        """Return how many values the caller is expecting.
        Adapted from the ompc project
        """
        import inspect, dis
        f = inspect.currentframe()
        # step into the function that called us
        # nout is two frames back
        f = f.f_back.f_back
        c = f.f_code
        i = f.f_lasti
        bytecode = c.co_code
        instruction = ord(bytecode[i+3])
        if instruction == dis.opmap['UNPACK_SEQUENCE']:
            howmany = ord(bytecode[i+4])
            return howmany
        elif instruction == dis.opmap['POP_TOP']:
            # OCTAVE always assumes at least 1 value
            return 1
        return 1
        
    def _make_octave_command(self, name, doc=None):
        """ Called by __getattr__ to create a wrapper to a matlab,
        procedure or object on the fly

        Adapted from the mlabwrap project
        """
        def octave_command(*args, **kwargs):
            kwargs['nout'] = self._get_nout()
            kwargs['verbose'] = False
            return self.call(name, *args, **kwargs)
        octave_command.__doc__ = "\n" + doc
        return octave_command

    def _get_doc(self, name):
        """ Attempt to get the documentation of a name
        Return None if the name does not exist
        """
        #print 'getting doc for', name
        if not self._session:
            return ''
        try:
            doc = self._eval('help %s' % name, verbose=False)
        except OctaveError:
            doc = self._eval('type %s' % name, verbose=False)
            # grab only the first line
            doc = doc.split('\n')[0]
        return doc

    def __getattr__(self, attr):
        """ Magically creates a wapper to an octave function, procedure or
        object on-the-fly.
        Adapted from the mlabwrap project
        """
        if re.search(r'\W', attr): # work around ipython <= 0.7.3 bug
            raise ValueError("Attributes don't look like this: %r" % attr)
        if attr.startswith('_'):
            raise AttributeError, attr
        # print_ -> print
        if attr[-1] == "_":
            name = attr[:-1]
        else:
            name = attr
        doc = self._get_doc(name)
        octave_command = self._make_octave_command(name, doc)
        #!!! attr, *not* name, because we might have python keyword name!
        setattr(self, attr, octave_command)
        return octave_command

    def __del__(self):
        close(self._session)
        

if __name__ == '__main__':
    from py2oct_demo import demo
    demo(delay=2)
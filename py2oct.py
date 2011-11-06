import os
import subprocess
import sys
import atexit
import re
import pdb
import numpy as np
try:
    import h5py
except:
    'Please install h5py from "http://code.google.com/p/h5py/downloads/list"'
    raise

# TODO: test, documentation, setup.py, add to bitbucket, send linFk to Scipy
#       add a test harness - simple functions, dictionaries,
#       nested dictionaries
#       cell arrays in dictionaries, cell arrays, scripts, functions
# NOTE: talk about the limitations of Octave up front - nested functions class
# TODO: Do a try/catch block in an m-file and capture the error


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


class Octave(object):

    def __init__(self):
        self._session = self.start_octave()

    def start_octave(self):
        ''' Start an octave session in a subprocess and return the handle

        Attempts to call "octave" or raise an error
        '''
        # try to load octave
        # -q is quiet startup, --braindead is Matlab compatibilty mode
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

        The function must have documentation, or we ca

        The first command will take about 0.5s for Octave to load up.
        The subsequent commands will be much faster.

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

        # create our temporary hdf files
        in_file = '__input__.hdf'
        out_file = '__output__.hdf'
        for fname in in_file, out_file:
            if os.path.exists(fname):
                os.remove(fname)

        # these three lines will form the commands sent to Octave
        # load("-hdf5", "infile", "invar1", ...)
        # [a, b, c] = foo(A, B, C)
        # save("-hdf5", "outfile", "outvar1", ...)
        load_line = []
        call_line = []
        save_line = []

        if nout:
            # create a dummy list of var names ("a", "b", "c", ...)
            # use ascii char codes so we can increment
            argout_list = []
            ascii_code = 97
            for i in range(nout):
                argout_list.append(chr(ascii_code))
                ascii_code += 1
            call_line.append('[')
            call_line.append(', '.join(argout_list))
            call_line.append('] = ')
            save_line.append('save "-hdf5" "%s" "' % out_file)
            save_line.append('" "'.join(argout_list))
            save_line.append('"')

        if inputs:
            fid = h5py.File(in_file, "w")
            # create a dummy list of var names ("A", "B", "C" ...)
            # use ascii char codes so we can increment
            argin_list = []
            ascii_code = 65
            for var in inputs:
                argin_list.append(chr(ascii_code))
                pdb.set_trace()
                # for structs - recursively add the elements
                if isinstance(var, dict):
                    sub = fid.create_group(chr(ascii_code))
                    self._putvals(sub, var)
                else:
                    self._putval(sub, chr(ascii_code), var)
                    fid.create_dataset(chr(ascii_code), data=var)
                ascii_code += 1
            fid.close()
            load_line.append('load "-hdf5" "%s" "' % in_file)
            load_line.append('" "'.join(argin_list))  # A, B, C, ...
            load_line.append('"')
            call_line.append('%s(' % func)  # foo
            call_line.append(', '.join(argin_list))  # A, B, C, ...
            call_line.append(')')
        else:
            # foo - no arguments
            call_line += '%s()' % func
            
        # create the command and execute in octave
        cmd = []
        if load_line:
            cmd.append(''.join(load_line))
        cmd.append(''.join(call_line))
        if save_line:
            cmd.append(''.join(save_line))
        resp = self._eval(cmd, verbose=verbose)

        if inputs:
            os.remove(in_file)

        if nout and self._session and not resp == 'error':
            fid = h5py.File(out_file)
            outputs = []
            for arg in argout_list:
               
               try:
                   val = self._getval(fid[arg])
               except:
                   pdb.set_trace()
                   val = self._getvals(fid[arg]['value'])
               outputs.append(val)
            fid.close()
            os.remove(out_file)
            if len(outputs) > 1:
                return tuple(outputs)
            else:
                return outputs[0]
        output = None
        if nout:
            output = tuple((None for i in range(nout)))
        return output
        
    def _getval(self, group):
        ''' Handle variable types that do not translate directly
        '''
        type_ = group['type'].value
        val = group['value'].value
        
        # strings come in as byte arrays
        if type_ == 'sq_string':
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
        
    def _putval(self, group, name, data):
        ''' Handle variable types that do not translate directly
        '''
        # the last char is stripped off in transit
        if isinstance(data, str):
            data += '_'
        # lists get mangled unless you make them an ndarray
        # NOTE: they will still get mangled for cell arrays
        elif isinstance(data, list):
            data = np.array(data)
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
        
    def _putvals(self, group, dict_):
        ''' Put a nested dict into the HDF file as a struct
        '''
        for key in dict_.keys():
            pdb.set_trace()
            if isinstance(dict_[key], dict):
                sub = group.create_group(key)
                self._putvals(sub, dict_[key])
            else:
                self._putval(group, key, dict_[key])

    def _getvals(self, group):
       ''' Extract a nested struct / cell array from the HDF file

       Structs become dictionaries, cell arrays become lists
       '''
       #pdb.set_trace()
       data = OctaveStruct()
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
       # handle cell arrays
       if 'dims' in data:
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
        
    def _make_octave_command(self, name, doc=None):
        """ Called by __getattr__ to create a wrapper to a matlab,
        procedure or object on the fly

        Adapted from the mlabwrap project
        """
        def octave_command(*args, **kwargs):
            kwargs['nout'] = self._get_nout()
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
            doc = self._eval('help %s' % name)
        except OctaveError:
            doc = self._eval('type %s' % name)
            # grab only the first line
            doc = doc.split('\n')[0]
        return doc

    def _dummy(self, name=None):
        def dummy():
            nout = self._get_nout()
            if nout > 1:
                return tuple(None for i in range(nout))
        #print name
        dummy.__doc__ = ('Octave does not contain the function, '
                        'procedure, or object "%s"' % name)
        return dummy

    def _eval(self, cmds, verbose=False):
        if isinstance(cmds, str):
            cmds = cmds.split('\n')
        resp = []
        for cmd in cmds:
            # use ascii code 201 to signal an error and 200 
            # to signal action complete
            eval_ = "eval('%s; disp(char(200))', 'disp(char(201))')\n" % cmd
            self._session.stdin.write(eval_)
            #pdb.set_trace()
            while 1:
                line = self._session.stdout.readline().rstrip()
                #import pdb; pdb.set_trace()
                if line == chr(200):
                    break
                elif line == chr(201):
                    raise OctaveError('Octave returned an error for %s' % cmd)
                elif verbose:
                    print line
                resp.append(line)
        return '\n'.join(resp)

    def __getattr__(self, attr):
        """ Magically creates a wapper to an octave function, procedure or
        object on-the-fly.
        Adapted from the mlabwrap project
        """
        if re.search(r'\W', attr): # work around ipython <= 0.7.3 bug
            raise ValueError("Attributes don't look like this: %r" % attr)
        if attr.startswith('__'):
            raise AttributeError, attr
        assert not attr.startswith('_') # XXX
        # print_ -> print
        if attr[-1] == "_":
            name = attr[:-1]
        else:
            name = attr
        doc = self._get_doc(name)
        #print 'doc:', doc
        if not doc == 'error':
            octave_command = self._make_octave_command(name, doc)
            #!!! attr, *not* name, because we might have python keyword name!
            setattr(self, attr, octave_command)
            return octave_command
        else:
            dummy = self._dummy(name)
            return dummy

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

    def __del__(self):
        close(self._session)


if __name__ == '__main__':
    from pprint import pprint
    x = 2.
    y = 2.
    octave = Octave()
    #pdb.set_trace()
    out = octave.test_datatypes()
    pprint(out)
    pdb.set_trace()
    '''
    a = octave.zeros(3,3)
    print a
    try:
        help(octave.disp2)
    except OctaveError:
        print 'oopsy'
    a = octave.call('zeros', 1, verbose=True)
    print a
    # XXX the error is here
    #pdb.set_trace()
    help(octave.bar)
    print 'calling bar'
    try:
        d  = octave.call('bar',  x, verbose=True)
    except OctaveError:
        print 'woops'
    a, b, c, d= None, None, None, None
    #a, b = octave.call('foo', x, verbose=True)
    print 'calling ones'
    
    #c = octave.call('ones', x, y, verbose=True)
    print 'a', a, type(a)
    print 'b', b, type(b)
    print 'c', c, type(c)
    #print c[0], type(c[0])
    print 'd', d
    '''

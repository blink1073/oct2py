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

# TODO: test, documentation, setup.py, add to bitbucket, send linFk to Scipy
#       add a test harness - simple functions, dictionaries,
#       nested dictionaries
#       cell arrays in dictionaries, cell arrays, scripts, functions
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


class Octave(object):

    def __init__(self):
        ''' Start an octave session in a subprocess

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
        self._session = session
        
    def run(self, script, **kwargs):
        ''' Runs a script or an m-file
        
        Keywords implemented:
            verbose : If true, all m-file prints will be displayed
            
        '''
        # don't return a value from a script
        kwargs['nout'] =0
        # this line is needed to force the plot to display
        for cmd in ['gplot', 'plot', 'bar', 'contour', 'hist', 'loglog', 
                    'polar', 'semilogx', 'stairs', 'gsplot', 'mesh', 
                    'meshdom']:
            if cmd in script:
                script += ';print -deps foo.eps;'
                break
        self.call(script, **kwargs)
        
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
                #pdb.set_trace()
                # for structs - recursively add the elements
                if isinstance(var, dict):
                    sub = fid.create_group(chr(ascii_code))
                    self._putvals(sub, var)
                else:
                    self._putval(fid, chr(ascii_code), var)
                ascii_code += 1
            fid.close()
            load_line.append('load "-hdf5" "%s" "' % in_file)
            load_line.append('" "'.join(argin_list))  # A, B, C, ...
            load_line.append('"')
            call_line.append('%s(' % func)  # foo
            call_line.append(', '.join(argin_list))  # A, B, C, ...
            call_line.append(');')
        elif nout:
            # call foo() - no arguments
            call_line += '%s();' % func
        else:
            # run foo
            call_line += '%s;' % func
        # this line is needed to force the plot to display
        if func in ['gplot', 'plot', 'bar', 'contour', 'hist', 'loglog', 
                    'polar', 'semilogx', 'stairs', 'gsplot', 'mesh', 
                    'meshdom']:
            call_line += ';print -deps foo.eps;'
            
        # create the command and execute in octave
        cmd = []
        if load_line:
            cmd.append(''.join(load_line))
        cmd.append(''.join(call_line))
        if save_line:
            cmd.append(''.join(save_line))
        self._eval(cmd, verbose=verbose)
            
        if inputs:
            os.remove(in_file)

        if nout:
            fid = h5py.File(out_file)
            outputs = []
            for arg in argout_list:
               try:
                   val = self._getval(fid[arg])
               except:
                   val = self._getvals(fid[arg]['value'])
               outputs.append(val)
            fid.close()
            os.remove(out_file)
            if len(outputs) > 1:
                return tuple(outputs)
            else:
                return outputs[0]
        
    def _putval(self, group, name, data):
        ''' Handle variable types that do not translate directly
        '''
        # the last char is stripped off in transit
        if isinstance(data, str):
            data += '_'
        # lists get mangled unless you make them an ndarray
        # XXX NOTE: they will still get mangled for cell arrays
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
            if isinstance(dict_[key], dict):
                sub = group.create_group(key)
                self._putvals(sub, dict_[key])
            else:
                self._putval(group, key, dict_[key])

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

    def _eval(self, cmds, verbose=False):
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
        octave_command = self._make_octave_command(name, doc)
        #!!! attr, *not* name, because we might have python keyword name!
        setattr(self, attr, octave_command)
        return octave_command

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
    oc = Octave()
    #pdb.set_trace()
    import time
    time.sleep(1)  
    
    # speed checks
    raws = """
    disp('Eig');tic;data=rand(500,500);eig(data);toc;
    disp('Svd');tic;data=rand(500,500);[u,s,v]=svd(data);s=svd(data);toc;
    disp('Inv');tic;data=rand(1000,1000);result=inv(data);toc;
    disp('Det');tic;data=rand(1000,1000);result=det(data);toc;
    disp('Dot');tic;a=rand(1000,1000);b=inv(a);result=a*b-eye(1000);toc;
    """
    wrapped = """
    data=oc.rand(500,500); oc.eig(data);
    data=oc.rand(500,500); (u,s,v)=oc.svd(data); s=oc.svd(data);
    data=oc.rand(1000,1000); result=oc.inv(data);
    data=oc.rand(1000,1000); result=oc.det(data);
    a=oc.rand(1000,1000); b=oc.inv(a); result=(oc.dot(a,b)-oc.eye(1000))
    """
    '''
    runs = zip(raws.split('\n'), wrapped.split('\n'))
    for run in runs:
        if run[0].strip():
            t1 = time.clock()
            oc.run(run[0], verbose=True)
            raw = time.clock() - t1
            print "Raw:", raw
            t1 = time.clock()
            exec(run[1].strip())
            wrapped = time.clock() -t1 
            print "Wrapped:", wrapped
            print "Penalty: %s%%" % int(((wrapped - raw) / raw) * 100)
    '''
    
    out = oc.test_datatypes()
    pprint(out)
    
    # next, we traverse through "out", calling roundtrip.m, making sure it 
    # comes back the same - value and type
    def check_data(data):
        for key in sorted(data.keys()):
            if key in ['cell', 'char_array', 'cell_array', 'basic', 'name']:
                continue
            elif isinstance(data[key], dict):
                print 'Checking dictionary: ', key
                check_data(data[key])
            else:
                print 'Checking:', key
                result = oc.roundtrip(data[key])
                try:
                    if isinstance(data[key], np.ndarray):
                        assert data[key].dtype == result.dtype
                    assert data[key] == result
                    assert type(data[key]) == type(result)
                except ValueError:
                    assert np.allclose(data[key], result)
                except AssertionError:
                    # need to test for NaN explicitly
                    if np.isnan(result) and np.isnan(data[key]):
                        pass
                    # floats are converted to doubles by Matlab
                    elif (type(data[key]) == np.float32 and 
                          type(result) == np.float64):
                        pass
                    else:
                        raise
    check_data(out)
    
    '''
    a = oc.zeros(3,3)
    print a
    try:
        help(oc.disp2)
    except OctaveError:
        print 'oopsy'
    a = oc.call('zeros', 1, verbose=True)
    print a
    # XXX the error is here
    #pdb.set_trace()
    help(oc.bar)
    print 'calling bar'
    try:
        d  = oc.call('bar',  x, verbose=True)
    except OctaveError:
        print 'woops'
    a, b, c, d= None, None, None, None
    #a, b = oc.call('foo', x, verbose=True)
    print 'calling ones'
    
    #c = oc.call('ones', x, y, verbose=True)
    print 'a', a, type(a)
    print 'b', b, type(b)
    print 'c', c, type(c)
    #print c[0], type(c[0])
    print 'd', d
    '''

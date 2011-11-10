import glob
import os
import subprocess
import sys
try:
    import h5py
except ImportError:
    IMPORT_ERROR = 'Error: please install h5py\n'
    IMPORT_ERROR += '"using setuptools: easy_install h5py"'
    print IMPORT_ERROR
else:
    IMPORT_ERROR = False


def call(func, *inputs, **kwargs):
    """  Calls an M file using Octave
    If inputs are provided, they are passed to octave
       Pass in the inputs as unnamed parameters after the function name
    If nargout is in the keyword args,
       returns a single variable if nargout == 1
       returns a tuple of variables in nargout > 1
    If verbose is in the keyword args, the response from octave will be printed
    Uses HDF5 files to pass data between Octave and Numpy

    Note: The function must either exist as an m-file in this directory or on
    Octave's path.

    Usage:

      >> import octave
      >> x = 2
      >> y = 1
      >> a = octave.call('zeros', x, y, nargout=1, verbose=True)

      array([[ 0.,  0.]])
      >> print a
      [[ 0.  0.]]
    """
    if IMPORT_ERROR:
        print IMPORT_ERROR
        return

    # try to find octave
    if 'octave' in os.environ['PATH'].lower():
        octave_path = 'octave'
    elif 'win32' in sys.platform:
        octave_path = glob.glob('c:/Octave/*/bin/octave.exe')[0]
        if not os.path.exists(octave_path):
            print 'Please install Octave at "c:/Octave" or put it in your path'
            print 'setx PATH %PATH%;<path-to-octave-bin-folder>'
        return
    else:
        print 'Please put Octave executable in your PATH'
        return

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

    if 'nargout' in kwargs.keys():
        # create a dummy list of var names ("a", "b", "c", ...)
        # use ascii char codes so we can increment
        argout_list = []
        ascii_code = 97
        for i in range(kwargs['nargout']):
            argout_list.append(chr(ascii_code))
            ascii_code += 1
        call_line.append('[')
        call_line.append(', '.join(argout_list))
        call_line.append('] = ')
        save_line.append('save "-hdf5" "{0}" "'.format(out_file))
        save_line.append('" "'.join(argout_list))
        save_line.append('"\n')

    if inputs:
        fid = h5py.File(in_file, "w")
        # create a dummy list of var names ("A", "B", "C" ...)
        # use ascii char codes so we can increment
        argin_list = []
        ascii_code = 65
        for var in inputs:
            argin_list.append(chr(ascii_code))
            fid.create_dataset(chr(ascii_code), data=var)
            ascii_code += 1
        fid.close()
        load_line.append('load "-hdf5" "{0}" "'.format(in_file))
        load_line.append('" "'.join(argin_list))  # A, B, C, ...
        load_line.append('"\n')
        call_line.append('{0}('.format(func))   # foo(
        call_line.append(', '.join(argin_list))  # A, B, C, ...
        call_line.append(');\n')
    else:
        # foo() - no arguments
        call_line = '{0}()'.format(func)

    # create the command and execute in octave
    cmd = []
    cmd.append(''.join(load_line))
    cmd.append(''.join(call_line))
    cmd.append('disp(a)\n')
    cmd.append(''.join(save_line))
    proc = subprocess.Popen('{0} -q'.format(octave_path),
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    resp, err = proc.communicate(''.join(cmd))
    if 'verbose' in kwargs and kwargs['verbose']:
        print resp
    if err:
        print 'Octave error:', err

    if inputs:
        os.remove(in_file)

    if 'nargout' in kwargs:
        print out_file
        fid = h5py.File(out_file)
        outputs = []
        for arg in argout_list:
            try:
                val = fid[arg]['value'].value
                outputs.append(val)
            except AttributeError:
                # this is a dict or cell array - unravel it
                outputs.append(_todict(fid, '{0}/value'.format(arg)))
            # don't break the whole thing for one failure
            except Exception as e:
                print e
                outputs.append(None)
        fid.close()
        os.remove(out_file)
        if len(outputs) > 1:
            return tuple(outputs)
        else:
            return outputs[0]
    return


def _todict(fid, path):
        ''' Extract an arbitrarily nested dict / cell array from the HDF file
        '''
        data = {}
        for key in fid[path].keys():
            location = '{0}/{1}/value/_0/value'.format(path, key)
            try:
                val = fid[location].value
                data[key] = val
            except AttributeError:
                data[key] = _todict(fid, location)
            except KeyError:
                # this is a cell array - change the location
                if '_' in key:
                    location = '{0}/{1}/value'.format(path, key)
                    val = fid[location].value
                    data[int(key[1:])] = val
            # don't break the whole thing for an uncaught error
            except Exception as e:
                print e
                data[val] = None
        return data


if __name__ == '__main__':
    import time
    t1 = time.time()
    x = 2.
    y = 2.

    print time.time() - t1
    a, b = call('foo', x, nargout=2, verbose=True)
    print time.time() - t1
    a, b = call('foo', x, nargout=2, verbose=True)
    print time.time() - t1
    c = call('ones', x, y, nargout=1, verbose=True)
    a = call('zeros', 1, 3, nargout=1, verbose=True)
    print a
    a = call('zeros', 1, 4, nargout=1)
    print a
    a = call('zeros', 1, 5, nargout=1)
    print a
    a = call('zeros', 1, 6, nargout=1)
    print a
    a = call('zeros', 1, 7, nargout=1)
    print 'a', a, type(a)
    print 'b', b, type(b)
    print 'c', c, type(c)
    print c[0], type(c[0])

    print time.time() - t1


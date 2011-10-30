import glob
import os
import subprocess
import sys
import h5py


# TODO: test, documentation, setup.py, add to bitbucket, send link to Scipy
#       add a test harness - simple functions, dictionaries,
#       nested dictionaries
#       cell arrays in dictionaries, cell arrays, scripts, functions
# NOTE: talk about the limitations of Octave up front - nested functions
class Octave(object):

    def __init__(self):
        self._proc = None
        self.start_octave()

    def start_octave(self):
        # try to find octave
        if 'octave' in os.environ['PATH'].lower():
            octave_path = 'octave'
        elif 'win32' in sys.platform:
            octave_path = glob.glob('c:/Octave/*/bin/octave.exe')[0]
            if not os.path.exists(octave_path):
                print 'Please install Octave at "c:/Octave" '
                print '  or put it in your path:'
                print 'setx PATH %PATH%;<path-to-octave-bin-folder>'
                return
        else:
            print 'Please put the Octave executable in your PATH'
            return
        # -q is quiet startup, --braindead is Matlab compatibilty mode
        cmd = '{0} -q --braindead'.format(octave_path)
        self._proc = subprocess.Popen(cmd, shell=True,
                                     stderr=subprocess.STDOUT,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)

    def call(self, func, *inputs, **kwargs):
        """  Calls an M file using Octave
        If inputs are provided, they are passed to octave
           Pass in the inputs as unnamed parameters after the function name
        If nargout is in the keyword args, it changes the number
           of variables returned (default is 1).
           If nargin > 1, a tuple will be returned
        If verbose is in the keyword args, the response from octave
           will be printed

        Uses HDF5 files to pass data between Octave and Numpy - requires h5py

        Notes:
        The function must either exist as an m-file in this directory or
        on Octave's path.
        You can add to the path by calling the add_path method.
        The first command will take about 0.5s for Octave to load up.
        The subsequent commands will be much faster.

        Usage:

          >> import octave
          >> x = 2
          >> y = 1
          >> a = octave.call('zeros', x, y, nargout=1, verbose=True)

          array([[ 0.,  0.]])
          >> print a
          [[ 0.  0.]]
        """
        # Don't call if octave isn't running (bad path or an error)
        if not self._proc:
            output = None
            print "Error - octave unavailable"
            if 'nargout' in kwargs:
                output = tuple((None for i in range(kwargs['nargout'])))
            return output

        # default to one output argument
        if 'nargout' in kwargs:
            nargout = kwargs['nargout']
        else:
            nargout = 1
        if 'verbose' in kwargs:
            verbose = kwargs['verbose']
        else:
            verbose = False

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

        if nargout:
            # create a dummy list of var names ("a", "b", "c", ...)
            # use ascii char codes so we can increment
            argout_list = []
            ascii_code = 97
            for i in range(nargout):
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
            # foo - no arguments
            call_line = '{0}\n'.format(func)

        # create the command and execute in octave
        cmd = []
        cmd.append(''.join(load_line))
        cmd.append(''.join(call_line))
        cmd.append(''.join(save_line))
        # add this as a flag for when it is finished
        done_str = '6U1S754Z4UKKU911K4\n'
        cmd.append("disp {0}".format(done_str))
        self._proc.stdin.write(''.join(cmd))

        while 1:  # wait for the done_str output or an error
            line = self._proc.stdout.readline()
            if line == done_str:
                break
            if verbose or ('error:' in line):
                print line
                if 'error: ' in line:
                    self._proc = None
                    break

        if inputs:
            os.remove(in_file)

        if nargout and self._proc:
            fid = h5py.File(out_file)
            outputs = []
            for arg in argout_list:
                try:
                    val = fid[arg]['value'].value
                    outputs.append(val)
                except AttributeError:
                    # this is a dict or cell array - unravel it
                    outputs.append(self._todict(fid, '{0}/value'.format(arg)))
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
        output = None
        if nargout:
            output = tuple((None for i in range(nargout)))
        return output

    def _todict(self, fid, path):
            ''' Extract a nested dict / cell array from the HDF file
            '''
            data = {}
            for key in fid[path].keys():
                location = '{0}/{1}/value/_0/value'.format(path, key)
                try:
                    val = fid[location].value
                    data[key] = val
                except AttributeError:
                    data[key] = self._todict(fid, location)
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

    def addpath(self, path):
        """ Add a path to Octave for processing scripts in another dir
        """
        if not self._proc:
            return
        self._proc.write('addpath("{0}"\n')

    def __del__(self):
        try:
            self._proc.stdin.write('exit')
        except:
            pass

if __name__ == '__main__':
    x = 2.
    y = 2.
    octave = Octave()
    octave.call('zeros', 1, verbose=True)
    d = octave.call('bar',  verbose=True)
    a, b = octave.call('foo', x, nargout=2, verbose=True)
    c = octave.call('ones', x, y, verbose=True)
    print 'a', a, type(a)
    print 'b', b, type(b)
    print 'c', c, type(c)
    print c[0], type(c[0])
    print 'd', d

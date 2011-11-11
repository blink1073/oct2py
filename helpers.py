''' helpers - Miscellaneous helper constructs

_open  - called to open an Octave session
_close - called to close an Octave session atexit or when an octave object is
        deleted
_get_nout - used to detect the number of output arguments requested on a
            function call
OctaveError - used to raise Octave specific errors
OctaveStruct - new object type that supports dictionary and attribute based
                access, allowing it to be used like an Octave structure
'''
import os
import subprocess
import atexit
import inspect
import dis
import re
from glob import glob


def _open():
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
    atexit.register(lambda handle=session: _close(handle))
    return session


def _close(handle):
    """ Closes an octave session

    Called when the octave object is deleted or at program exit
    """
    try:
        handle.stdin.write('exit')
    except ValueError:
        pass


def _get_nout():
    """ Return how many values the caller is expecting.
    Adapted from the ompc project
    """
    frame = inspect.currentframe()
    # step into the function that called us
    # nout is two frames back
    frame = frame.f_back.f_back
    bytecode = frame.f_code.co_code
    instruction = ord(bytecode[frame.f_lasti + 3])
    if instruction == dis.opmap['UNPACK_SEQUENCE']:
        howmany = ord(bytecode[frame.f_lasti + 4])
        return howmany
    elif instruction == dis.opmap['POP_TOP']:
        # OCTAVE always assumes at least 1 value
        return 1
    return 1
    
def _remove_hdfs(type_):
    """ Remove any HDF files in this directory that we have created """
    files = os.listdir(os.getcwd())
    for fname in files:
        if re.match(r'%s_\d{12}.hdf' % type_, fname):
            try:
                os.remove(fname)
            except OSError:
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

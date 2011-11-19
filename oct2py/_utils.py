''' helpers - Miscellaneous helper constructs
'''
import os
import time
import subprocess
import random
import atexit
import inspect
import dis
import re
from glob import glob


def open_():
    ''' Start an octave session in a subprocess

    Attempts to call "octave" or raise an error
     -q is quiet startup, --braindead is Matlab compatibilty mode

    Note
    ====
    On Windows, it attempts to find octave in c:\Octave if it is not
        on the path

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
            raise Oct2PyError(msg)
        else:
            cmd = 'octave -q --braindead'
            session = subprocess.Popen(cmd, shell=True,
                                 stderr=subprocess.STDOUT,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE)
    except OSError:
        raise Oct2PyError('Please put the Octave executable in your PATH')
    return session


def register_del(fname):
    """ Register an HDF file for deletion at program exit

    Parameters
    ==========
    fname : str
        Name of file to register
    """
    atexit.register(lambda filename=fname: remove_hdfs(filename))


def remove_hdfs(filename=None):
    """ Remove the desired file and any HDFs that haven't been accessed in
    over a minute

    Parameters
    ==========
    filename : str
        Optional specific file to delete
    """
    try:
        os.remove(filename)
    except OSError:
        pass
    files = os.listdir(os.getcwd())
    for fname in files:
        if re.match(r'(load|save)_.{10}\.hdf', fname):
            if (time.time() - os.path.getatime(fname) > 60):
                try:
                    os.remove(fname)
                except OSError:
                    pass


def get_nout():
    """ Return how many values the caller is expecting.
    Adapted from the ompc project

    Returns
    ======
    Number of arguments expected by caller, default is 1

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


def create_hdf(type_):
    """ Create an HDF file of the given type with a random name

    Parameters
    ==========
    type_ : str
        'load' or 'save' type file

    Returns
    =======
    Random HDF file name "load_##########.hdf" or "save_##########.hdf"

    """
    name = [type_, '_']
    name.extend([str(random.choice(range(10))) for x in range(10)])
    name.append('.hdf')
    return ''.join(name)


class Oct2PyError(Exception):
    """ Called when we can't open Octave or octave throws an error """
    pass


class Struct(dict):
    '''
    Octave style struct.
    --------------------
    Supports dictionary and attribute style access.

    Usage
    -----
    >>> from oct2py import Struct
    >>> a = Struct()
    >>> a.b = 'spam'  # a["b"] == 'spam'
    >>> a.c["d"] = 'eggs'  # a.c.d == 'eggs'

    '''
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            if not attr.startswith('_'):
                self[attr] = Struct()
                return self[attr]
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

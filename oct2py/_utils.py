"""
.. module:: _utils
   :synopsis: Miscellaneous helper constructs

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
import os
import time
import subprocess
import random
import atexit
import inspect
import dis
import re
import sys
from glob import glob

sys.path.append('..')


def _open():
    """
    Start an octave session in a subprocess.

    Returns
    =======
    out : fid
        File descriptor for the Octave subprocess

    Raises
    ======
    Oct2PyError
        If the session is not opened sucessfully.

    Notes
    =====
    Options sent to Octave: -q is quiet startup, --braindead is
    Matlab compatibilty mode.
    On Windows, it attempts to find octave in c:\Octave if it is not
    on the path.

    """
    session = None
    try:
        cmd = 'octave -q --braindead'
        session = subprocess.Popen(cmd, shell=True,
                                 stderr=subprocess.STDOUT,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 preexec_fn=os.setsid)
    except OSError:
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
                                 stdout=subprocess.PIPE,
                                 preexec_fn=os.setsid)
    except OSError:
        raise Oct2PyError('Please put the Octave executable in your PATH')
    return session


def _register_del(fname):
    """
    Register a MAT file for deletion at program exit.

    Parameters
    ==========
    fname : str
        Name of file to register.

    """
    atexit.register(lambda filename=fname: _remove_files(filename))


def _remove_files(filename=''):
    """
    Remove the desired file and any old MAT files.

    All MAT files in the current working directory over a minute old are
    deleted.
    This helps clean up orphaned HDF files in case the previous session did
    not close properly.

    Parameters
    ==========
    filename : str, optional
        Specific file to delete.

    """
    try:
        os.remove(filename)
    except OSError:
        pass
    files = os.listdir(os.getcwd())
    for fname in files:
        if re.match(r'(load|save)_.{10}\.(mat|hdf)', fname):
            try:
                atime = os.path.getatime(fname)
            except OSError:
                continue
            if (time.time() - atime > 60):
                try:
                    os.remove(fname)
                except OSError:
                    pass


def _get_nout():
    """
    Return the number of return values the caller is expecting.

    Adapted from the ompc project.

    Returns
    =======
    out : int
        Number of arguments expected by caller, default is 1.

    """
    frame = inspect.currentframe()
    # step into the function that called us
    # nout is two frames back
    frame = frame.f_back.f_back
    bytecode = frame.f_code.co_code
    try:
        instruction = ord(bytecode[frame.f_lasti + 3])
    except TypeError:
        instruction = ord(chr(bytecode[frame.f_lasti + 3]))
    if instruction == dis.opmap['UNPACK_SEQUENCE']:
        try:
            howmany = ord(bytecode[frame.f_lasti + 4])
        except TypeError:
            howmany = ord(chr(bytecode[frame.f_lasti + 4]))
        return howmany
    elif instruction == dis.opmap['POP_TOP']:
        # OCTAVE always assumes at least 1 value
        return 1
    return 1


def _create_file(type_, ext):
    """
    Create a file of the given type and extension with a random name.

    Parameters
    ==========
    type_ : str {'load', 'save'}
        Type of file to create (used for Octave 'save' or 'load' commands).
    ext : str {'mat', 'hdf'}
        File extension.

    Returns
    =======
    out : str
        Random MAT file name e.g. 'load_4932048302.mat'.

    """
    name = [type_, '_']
    name.extend([str(random.choice(range(10))) for x in range(10)])
    name.append('.{0}'.format(ext))
    return ''.join(name)


class Oct2PyError(Exception):
    """ Called when we can't open Octave or Octave throws an error
    """
    pass


class Struct(dict):
    """
    Octave style struct, enhanced.

    Supports dictionary and attribute style access.

    Examples
    ========
    >>> from oct2py import Struct
    >>> a = Struct()
    >>> a.b = 'spam'  # a["b"] == 'spam'
    >>> a.c["d"] = 'eggs'  # a.c.d == 'eggs'
    >>> print(a)
    {'c': {'d': 'eggs'}, 'b': 'spam'}

    """
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            if not attr.startswith('_'):
                self[attr] = Struct()
                return self[attr]
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def _test():
    """Run the doctests for this module
    """
    doctest.testmod()


if __name__ == "__main__":
    import doctest
    _test()

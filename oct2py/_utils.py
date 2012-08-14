"""
.. module:: _utils
   :synopsis: Miscellaneous helper constructs

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
import os
import subprocess
import inspect
import dis
import sys


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
    if 'linux' in sys.platform:
        session = subprocess.Popen('octave -q --braindead',
                                 shell=True,
                                 stderr=subprocess.STDOUT,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 preexec_fn=os.setsid)
    else:
        try:
            session = subprocess.Popen('octave -q --braindead',
                                 stderr=subprocess.STDOUT,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE)
        except OSError:
            msg = ('\n\nPlease install octave and put it in your path:\n'
                         'setx PATH "%PATH%;<path-to-octave-bin-dir>"\n\n')
            raise Oct2PyError(msg)
    return session


def _remove_tempdir():
    """
    Remove the files in the temporary directory

    Parameters
    ==========
    dir_ : str
        Folder to purge
    """
    import shutil
    import os
    dir_ = os.path.expanduser('~/oct2py_tmp')
    shutil.rmtree(dir_, ignore_errors=True)


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


def _create_file(ext):
    """
    Create a file of the given type and extension with a random name.
    Puts it in ~/.oct2py_files, a temporary directory

    Parameters
    ==========
    ext : str
        File extension (e.g.  'mat')

    Returns
    =======
    out : str
        Random file name with the desired extension

    """
    import tempfile
    dir_ = os.path.expanduser('~/oct2py_tmp')
    if not os.path.exists(dir_):
        os.mkdir(dir_)
    _, fname = tempfile.mkstemp(suffix='.' + ext, dir=dir_)
    return fname


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

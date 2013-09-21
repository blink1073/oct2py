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
import tempfile
import atexit


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

    """
    ON_POSIX = 'posix' in sys.builtin_module_names
    kwargs = dict(stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                  stdout=subprocess.PIPE, close_fds=ON_POSIX)
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs['startupinfo'] = startupinfo
    try:
        session = subprocess.Popen(['octave', '-q', '--braindead'], **kwargs)
    except OSError:
        msg = ('\n\nPlease install GNU Octave and put it in your path\n')
        raise Oct2PyError(msg)
    return session


def _remove_temp_files():
    """
    Remove the created mat files in the user's temp folder
    """
    import os
    import glob
    temp = tempfile.TemporaryFile()
    temp.close()
    dirname = os.path.dirname(temp.name)
    for fname in glob.glob(os.path.join(dirname, 'tmp*.mat')):
        try:
            os.remove(fname)
        except OSError:
            pass
        
        
atexit.register(_remove_temp_files)


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


def _create_file():
    """
    Create a MAT file with a random name.
    Puts it in if possible, or in ~/.oct2py_files

    Returns
    =======
    out : str
        Random file name with the desired extension
    """
    temp_file = tempfile.NamedTemporaryFile(suffix='.mat', delete=False)
    temp_file.close()
    return os.path.abspath(temp_file.name)


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

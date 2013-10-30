"""
.. module:: utils
   :synopsis: Miscellaneous helper constructs

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
import os
import inspect
import dis
import tempfile
import atexit


def _remove_temp_files():
    """
    Remove the created mat files in the user's temp folder
    """
    import os
    import glob
    temp = tempfile.NamedTemporaryFile()
    temp.close()
    dirname = os.path.dirname(temp.name)
    for fname in glob.glob(os.path.join(dirname, 'tmp*.mat')):
        try:
            os.remove(fname)
        except OSError:  # pragma: no cover
            pass


atexit.register(_remove_temp_files)


def get_nout():
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
    elif instruction == dis.opmap['STORE_NAME']:
        return 1
    elif instruction == dis.opmap['RETURN_VALUE']:
        return 1
    return 0


def create_file():
    """
    Create a MAT file with a random name in the temp directory

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


def get_log(name=None):
    """Return a console logger.

    Output may be sent to the logger using the `debug`, `info`, `warning`,
    `error` and `critical` methods.

    Parameters
    ----------
    name : str
        Name of the log.

    References
    ----------
    .. [1] Logging facility for Python,
           http://docs.python.org/library/logging.html

    """
    import logging

    if name is None:
        name = 'oct2py'
    else:
        name = 'oct2py.' + name

    log = logging.getLogger(name)
    log.setLevel(logging.WARN)
    return log


def _setup_log():
    """Configure root logger.

    """
    import logging
    import sys

    try:
        handler = logging.StreamHandler(stream=sys.stdout)
    except TypeError:  # pragma: no cover
        handler = logging.StreamHandler(strm=sys.stdout)

    log = get_log()
    log.addHandler(handler)
    log.setLevel(logging.WARN)
    log.propagate = False

_setup_log()


def _test():  # pragma: no cover
    """Run the doctests for this module
    """
    doctest.testmod()


if __name__ == "__main__":  # pragma: no cover
    import doctest
    _test()

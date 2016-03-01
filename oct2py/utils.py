"""
.. module:: utils
   :synopsis: Miscellaneous helper constructs

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
import inspect
import dis
import os
import stat
try:
    import pty
except ImportError:
    pty = None
from oct2py.compat import PY2


def get_nout():
    """
    Return the number of return values the caller is expecting.

    Adapted from the ompc project.

    Returns
    =======
    out : int
        Number of arguments expected by caller.

    """
    frame = inspect.currentframe()
    # step into the function that called us
    # nout is two frames back
    frame = frame.f_back.f_back
    bytecode = frame.f_code.co_code
    instruction = bytecode[frame.f_lasti + 3]
    instruction = ord(instruction) if PY2 else instruction
    if instruction == dis.opmap['UNPACK_SEQUENCE']:
        howmany = bytecode[frame.f_lasti + 4]
        howmany = ord(howmany) if PY2 else howmany
        return howmany
    elif instruction in [dis.opmap['POP_TOP'], dis.opmap['PRINT_EXPR']]:
        return 0
    return 1


class Oct2PyError(Exception):
    """ Called when we can't open Octave or Octave throws an error
    """
    pass


class Struct(dict):
    """
    Octave style struct, enhanced.

    Supports dictionary and attribute style access.  Can be pickled,
    and supports code completion in a REPL.

    Examples
    ========
    >>> from pprint import pprint
    >>> from oct2py import Struct
    >>> a = Struct()
    >>> a.b = 'spam'  # a["b"] == 'spam'
    >>> a.c["d"] = 'eggs'  # a.c.d == 'eggs'
    >>> pprint(a)
    {'b': 'spam', 'c': {'d': 'eggs'}}
    """
    def __getattr__(self, attr):
        """Access the dictionary keys for unknown attributes."""
        try:
            return self[attr]
        except KeyError:
            msg = "'Struct' object has no attribute %s" % attr
            raise AttributeError(msg)

    def __getitem__(self, attr):
        """
        Get a dict value; create a Struct if requesting a Struct member.

        Do not create a key if the attribute starts with an underscore.
        """
        if attr in self.keys() or attr.startswith('_'):
            return dict.__getitem__(self, attr)
        frame = inspect.currentframe()
        # step into the function that called us
        if frame.f_back.f_back and self._is_allowed(frame.f_back.f_back):
            dict.__setitem__(self, attr, Struct())
        elif self._is_allowed(frame.f_back):
            dict.__setitem__(self, attr, Struct())
        return dict.__getitem__(self, attr)

    def _is_allowed(self, frame):
        """Check for allowed op code in the calling frame"""
        allowed = [dis.opmap['STORE_ATTR'], dis.opmap['LOAD_CONST'],
                   dis.opmap.get('STOP_CODE', 0)]
        bytecode = frame.f_code.co_code
        instruction = bytecode[frame.f_lasti + 3]
        instruction = ord(instruction) if PY2 else instruction
        return instruction in allowed

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    @property
    def __dict__(self):
        """Allow for code completion in a REPL"""
        return self.copy()


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


def is_executable_file(path):
    """Checks that path is an executable regular file (or a symlink to a file).
    This is roughly ``os.path isfile(path) and os.access(path, os.X_OK)``, but
    on some platforms :func:`os.access` gives us the wrong answer, so this
    checks permission bits directly.
    """
    if not pty:
        return False

    # follow symlinks,
    fpath = os.path.realpath(path)

    # return False for non-files (directories, fifo, etc.)
    if not os.path.isfile(fpath):
        return False

    # On Solaris, etc., "If the process has appropriate privileges, an
    # implementation may indicate success for X_OK even if none of the
    # execute file permission bits are set."
    #
    # For this reason, it is necessary to explicitly check st_mode

    # get file mode using os.stat, and check if `other',
    # that is anybody, may read and execute.
    mode = os.stat(fpath).st_mode
    if mode & stat.S_IROTH and mode & stat.S_IXOTH:
        return True

    # get current user's group ids, and check if `group',
    # when matching ours, may read and execute.
    user_gids = os.getgroups() + [os.getgid()]
    if (os.stat(fpath).st_gid in user_gids and
            mode & stat.S_IRGRP and mode & stat.S_IXGRP):
        return True

    # finally, if file owner matches our effective userid,
    # check if `user', may read and execute.
    user_gids = os.getgroups() + [os.getgid()]
    if (os.stat(fpath).st_uid == os.geteuid() and
            mode & stat.S_IRUSR and mode & stat.S_IXUSR):
        return True

    return False


def which(filename):
    '''This takes a given filename; tries to find it in the environment path;
    then checks if it is executable. This returns the full path to the filename
    if found and executable. Otherwise this returns None.'''

    # Special case where filename contains an explicit path.
    if os.path.dirname(filename) != '' and is_executable_file(filename):
        return filename
    if 'PATH' not in os.environ or os.environ['PATH'] == '':
        p = os.defpath
    else:
        p = os.environ['PATH']
    pathlist = p.split(os.pathsep)
    for path in pathlist:
        ff = os.path.join(path, filename)
        if pty:
            if is_executable_file(ff):
                return ff
        else:
            pathext = os.environ.get('Pathext', '.exe;.com;.bat;.cmd')
            pathext = pathext.split(os.pathsep) + ['']
            for ext in pathext:
                if os.access(ff + ext, os.X_OK):
                    return ff + ext
    return None


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

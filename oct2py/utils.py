"""
.. module:: utils
   :synopsis: Miscellaneous helper constructs

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
import inspect
import dis
import sys

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
    if(sys.version_info >= (3, 6)):
        instruction = bytecode[frame.f_lasti + 2]
    else:
        instruction = bytecode[frame.f_lasti + 3]
    instruction = ord(instruction) if PY2 else instruction
    if instruction == dis.opmap['UNPACK_SEQUENCE']:
        if(sys.version_info >= (3, 6)):
            howmany = bytecode[frame.f_lasti + 3]
        else:
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


class StructArray(object):
    """A Python representation of an Octave structure array.

    Supports value access by index and accessing fields by name or value.

    This class is not meant to be directly created by the user.  It is
    created automatically for structure array values received from Octave.

    Examples
    ========
    >>> from oct2py import octave
    >>> # generate the struct array
    >>> octave.eval('foo = struct("bar", {1, 2}, "baz", {3, 4});')
    >>> foo = octave.pull('foo')
    >>> foo.bar  # value access
    [1.0, 2.0]
    >>> foo['baz']  # item access
    [3.0, 4.0]
    >>> foo[0]  # index access
    {'bar': 1.0, 'baz': 3.0}
    >>> foo[1].baz  # This is a Struct
    4.0
    """
    @classmethod
    def create(cls, value, extractor):
        """Initialize the struct array."""
        instance = StructArray()
        value = np.atleast_2d(value)
        instance._value = value
        instance._extractor = extractor
        return instance

    @property
    def fieldnames(self):
        return self._value.dtype.names

    @property
    def shape(self):
        return self._value.shape

    def __getattr__(self, attr):
        """Access the dictionary keys for unknown attributes."""
        try:
            return self[attr]
        except KeyError:
            msg = "'Struct' object has no attribute %s" % attr
            raise AttributeError(msg)

    def __getitem__(self, attr):
        """Get an item from the struct array."""

        # Get the values as a nested list.
        if attr in self.fieldnames:
            return self._extractor(self._value[attr])

        # Return simple items as structs
        if isinstance(attr, int):
            data = self._value.flatten()[attr]
            value = Struct()
            for (i, name) in enumerate(self.fieldnames):
                value[name] = self._extractor(data[i])
            return value

        else:
            # Use numpy indexing.
            data = self._value[attr]
            # Return a single value as a struct.
            if data.size == 1:
                value = Struct()
                for (i, name) in enumerate(self.fieldnames):
                    value[name] = self._extractor(data[i])
                return value
            return self._extractor(data)

    def __repr__(self):
        msg = 'x'.join(str(i) for i in self.shape)
        msg += ' struct array containing the fields:'
        for key in self.fieldnames:
            msg += '\n    %s' % key
        return msg

    @property
    def __dict__(self):
        """Allow for code completion in a REPL"""
        data = dict()
        for key in self.fieldnames:
            data[key] = None
        return data


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
    log.setLevel(logging.INFO)
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
    log.setLevel(logging.INFO)
    log.propagate = False

_setup_log()

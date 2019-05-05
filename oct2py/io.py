# -*- coding: utf-8 -*-
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

from __future__ import absolute_import, print_function, division

import inspect
import dis
import threading

import numpy as np
from scipy.io import loadmat, savemat
from scipy.io.matlab.mio5 import MatlabObject, MatlabFunction
from scipy.sparse import spmatrix

try:
    from pandas import Series, DataFrame
except Exception as e:
    class Series:
        pass
    class DataFrame:
        pass

from .compat import PY2
from .dynamic import OctaveVariablePtr, OctaveUserClass, OctaveFunctionPtr
from .utils import Oct2PyError


_WRITE_LOCK = threading.Lock()


def read_file(path, session=None):
    """Read the data from the given file path.
    """
    try:
        data = loadmat(path, struct_as_record=True)
    except UnicodeDecodeError as e:
        raise Oct2PyError(str(e))
    out = dict()
    for (key, value) in data.items():
        out[key] = _extract(value, session)
    return out


def write_file(obj, path, oned_as='row', convert_to_float=True):
    """Save a Python object to an Octave file on the given path.
    """
    data = _encode(obj, convert_to_float)
    try:
        # scipy.io.savemat is not thread-save.
        # See https://github.com/scipy/scipy/issues/7260
        with _WRITE_LOCK:
            savemat(path, data, appendmat=False, oned_as=oned_as,
                    long_field_names=True)
    except KeyError:  # pragma: no cover
        raise Exception('could not save mat file')


class Struct(dict):
    """
    Octave style struct, enhanced.

    Notes
    =====
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
        # Access the dictionary keys for unknown attributes.
        try:
            return self[attr]
        except KeyError:
            msg = "'Struct' object has no attribute %s" % attr
            raise AttributeError(msg)

    def __getitem__(self, attr):
        # Get a dict value; create a Struct if requesting a Struct member.
        # Do not create a key if the attribute starts with an underscore.
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
        # Check for allowed op code in the calling frame.
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
        # Allow for code completion in a REPL.
        return self.copy()


class StructArray(np.recarray):
    """A Python representation of an Octave structure array.

    Notes
    =====
    Accessing a record returns a Cell containing the values.
    This class is not meant to be directly created by the user.  It is
    created automatically for structure array values received from Octave.
    The last axis is squeezed if it is of size 1 to simplify element access.

    Examples
    ========
    >>> from oct2py import octave
    >>> # generate the struct array
    >>> octave.eval('x = struct("y", {1, 2}, "z", {3, 4});')
    >>> x = octave.pull('x')
    >>> x.y  # attribute access -> oct2py Cell
    Cell([[1.0, 2.0]])
    >>> x['z']  # item access -> oct2py Cell
    Cell([[3.0, 4.0]])
    >>> x[0, 0]  # index access -> numpy record
    (1.0, 3.0)
    >>> x[0, 1].z
    4.0
    """
    def __new__(cls, value, session=None):
        """Create a struct array from a value and optional Octave session."""
        value = np.asarray(value)
        # Squeeze the last element if it is 1
        if (value.shape[value.ndim - 1] == 1):
            value = value.squeeze(axis=value.ndim - 1)
        value = np.atleast_1d(value)

        if not session:
            return value.view(cls)

        # Extract the values.
        obj = np.empty(value.size, dtype=value.dtype).view(cls)
        for (i, item) in enumerate(value.ravel()):
            for name in value.dtype.names:
                obj[i][name] = _extract(item[name], session)
        return obj.reshape(value.shape)

    @property
    def fieldnames(self):
        """The field names of the struct array."""
        return self.dtype.names

    def __getattribute__(self, attr):
        """Return object arrays as cells and all other values unchanged.
        """
        attr = np.recarray.__getattribute__(self, attr)
        if isinstance(attr, np.ndarray) and attr.dtype.kind == 'O':
            return Cell(attr)
        return attr

    def __getitem__(self, item):
        """Return object arrays as cells and all other values unchanged.
        """
        item = np.recarray.__getitem__(self, item)
        if isinstance(item, np.ndarray) and item.dtype.kind == 'O':
            return Cell(item)
        return item

    def __repr__(self):
        shape = self.shape
        if len(shape) == 1:
            shape = (shape[0], 1)
        msg = 'x'.join(str(i) for i in shape)
        msg += ' StructArray containing the fields:'
        for key in self.fieldnames:
            msg += '\n    %s' % key
        return msg


class Cell(np.ndarray):
    """A Python representation of an Octave cell array.

    Notes
    =====
    This class is not meant to be directly created by the user.  It is
    created automatically for cell array values received from Octave.
    The last axis is squeezed if it is of size 1 to simplify element access.

    Examples
    ========
    >>> from oct2py import octave
    >>> # generate the struct array
    >>> octave.eval("x = cell(2,2); x(:) = 1.0;")
    >>> x = octave.pull('x')
    >>> x
    Cell([[1.0, 1.0],
           [1.0, 1.0]])
    >>> x[0]
    Cell([1.0, 1.0])
    >>> x[0].tolist()
    [1.0, 1.0]
    """
    def __new__(cls, value, session=None):
        """Create a cell array from a value and optional Octave session."""
        value = np.asarray(value, dtype=object)
        # Squeeze the last element if it is 1
        if (value.shape[value.ndim - 1] == 1):
            value = value.squeeze(axis=value.ndim - 1)
        value = np.atleast_1d(value)

        if not session:
            return value.view(cls)

        # Extract the values.
        obj = np.empty(value.size, dtype=object).view(cls)
        for (i, item) in enumerate(value.ravel()):
            obj[i] = _extract(item, session)
        return obj.reshape(value.shape)

    def __repr__(self):
        shape = self.shape
        if len(shape) == 1:
            shape = (shape[0], 1)
        msg = self.view(np.ndarray).__repr__()
        msg = msg.replace('array', 'Cell', 1)
        return msg.replace(', dtype=object', '', 1)


def _extract(data, session=None):
    """Convert the Octave values to values suitable for Python.
    """
    # Extract each item of a list.
    if isinstance(data, list):
        return [_extract(d, session) for d in data]

    # Ignore leaf objects.
    if not isinstance(data, np.ndarray):
        return data

    # Extract user defined classes.
    if isinstance(data, MatlabObject):
        cls = session._get_user_class(data.classname)
        return cls.from_value(data)

    # Extract struct data.
    if data.dtype.names:
        # Singular struct
        if data.size == 1:
            return _create_struct(data, session)
        # Struct array
        return StructArray(data, session)

    # Extract cells.
    if data.dtype.kind == 'O':
        return Cell(data, session)

    # Compress singleton values.
    if data.size == 1:
        return data.item()

    # Compress empty values.
    if data.size == 0:
        if data.dtype.kind in 'US':
            return ''
        return []

    # Return standard array.
    return data


def _create_struct(data, session):
    """Create a struct from session data.
    """
    out = Struct()
    for name in data.dtype.names:
        item = data[name]
        # Extract values that are cells (they are doubly wrapped).
        if isinstance(item, np.ndarray) and item.dtype.kind == 'O':
            item = item.squeeze().tolist()
        out[name] = _extract(item, session)
    return out


def _encode(data, convert_to_float):
    """Convert the Python values to values suitable to send to Octave.
    """
    ctf = convert_to_float

    # Handle variable pointer.
    if isinstance(data, (OctaveVariablePtr)):
        return _encode(data.value, ctf)

    # Handle a user defined object.
    if isinstance(data, OctaveUserClass):
        return _encode(OctaveUserClass.to_value(data), ctf)

    # Handle a function pointer.
    if isinstance(data, (OctaveFunctionPtr, MatlabFunction)):
        raise Oct2PyError('Cannot write Octave functions')

    # Handle matlab objects.
    if isinstance(data, MatlabObject):
        view = data.view(np.ndarray)
        out = MatlabObject(data, data.classname)
        for name in out.dtype.names:
            out[name] = _encode(view[name], ctf)
        return out

    # Integer objects should be converted to floats
    if isinstance(data, int):
        return float(data)

    # Handle pandas series and dataframes
    if isinstance(data, (DataFrame, Series)):
        return _encode(data.values, ctf)

    # Extract and encode values from dict-like objects.
    if isinstance(data, dict):
        out = dict()
        for (key, value) in data.items():
            out[key] = _encode(value, ctf)
        return out

    # Send None as nan.
    if data is None:
        return np.NaN

    # Sets are treated like lists.
    if isinstance(data, set):
        return _encode(list(data), ctf)

    # Lists can be interpreted as numeric arrays or cell arrays.
    if isinstance(data, list):
        if _is_simple_numeric(data):
            return _encode(np.array(data), ctf)
        return _encode(tuple(data), ctf)

    # Tuples are handled as cells.
    if isinstance(data, tuple):
        obj = np.empty(len(data), dtype=object)
        for (i, item) in enumerate(data):
            obj[i] = _encode(item, ctf)
        return obj

    # Sparse data must be floating type.
    if isinstance(data, spmatrix):
        return data.astype(np.float64)

    # Return other data types unchanged.
    if not isinstance(data, np.ndarray):
        return data

    # Extract and encode data from object-like arrays.
    if data.dtype.kind in 'OV':
        out = np.empty(data.size, dtype=data.dtype)
        for (i, item) in enumerate(data.ravel()):
            if data.dtype.names:
                for name in data.dtype.names:
                    out[i][name] = _encode(item[name], ctf)
            else:
                out[i] = _encode(item, ctf)
        return out.reshape(data.shape)

    # Complex 128 is the highest supported by savemat.
    if data.dtype.name == 'complex256':
        return data.astype(np.complex128)

    # Convert to float if applicable.
    if ctf and data.dtype.kind in 'ui':
        return data.astype(np.float64)

    # Return standard array.
    return data


def _is_simple_numeric(data):
    """Test if a list contains simple numeric data."""
    for item in data:
        if isinstance(item, set):
            item = list(item)
        if isinstance(item, list):
            if not _is_simple_numeric(item):
                return False
        elif not isinstance(item, (int, float, complex)):
            return False
    return True

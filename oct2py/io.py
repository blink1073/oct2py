# -*- coding: utf-8 -*-
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

from __future__ import absolute_import, print_function, division

import inspect
import dis

import numpy as np
from scipy.io import loadmat, savemat
from scipy.sparse import spmatrix

from .compat import PY2
from .dynamic import OctaveVariablePtr, OctaveUserClass
from .utils import Oct2PyError


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
    Differs from numpy indexing in that a single number index
    is used to find the nth element in the array, mimicking
    the behavior of a struct array in Octave.

    This class is not meant to be directly created by the user.  It is
    created automatically for structure array values received from Octave.

    Examples
    ========
    >>> from oct2py import octave
    >>> # generate the struct array
    >>> octave.eval('foo = struct("bar", {1, 2}, "baz", {3, 4});')
    >>> foo = octave.pull('foo')
    >>> foo.bar  # attribute access
    [1.0, 2.0]
    >>> foo['baz']  # item access
    [3.0, 4.0]
    >>> el = foo[0]  # index access
    >>> foo[1]['baz']
    4.0
    """
    def __new__(cls, value, session=None):
        """Create a struct array from a value and optional Octave session."""
        value = np.asarray(value)

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

    def __getitem__(self, attr):
        # Support int based indexing by absolute position.
        if isinstance(attr, int):
            if abs(attr) >= self.size:
                raise IndexError('Index out of range')
            index = np.unravel_index(attr % self.size, self.shape)
            return self[index]
        return np.recarray.__getitem__(self, attr)

    def __repr__(self):
        shape = self.shape
        if len(shape) == 1:
            shape = (shape, 1)
        msg = 'x'.join(str(i) for i in shape)
        msg += ' StructArray containing the fields:'
        for key in self.fieldnames:
            msg += '\n    %s' % key
        return msg


class Cell(np.ndarray):
    """A Python representation of an Octave cell array.

    Notes
    =====
    Differs from numpy indexing in that a single number index
    is used to find the nth element in the array, mimicking
    the behavior of a cell array in Octave.

    This class is not meant to be directly created by the user.  It is
    created automatically for cell array values received from Octave.
    """
    def __new__(cls, value, session=None):
        """Create a cell array from a value and optional Octave session."""
        value = np.asarray(value, dtype=object)

        if not session:
            return value.view(cls)

        # Extract the values.
        obj = np.empty(value.size, dtype=object).view(cls)
        for (i, item) in enumerate(value.ravel()):
            obj[i] = _extract(item, session)
        return obj.reshape(value.shape)

    def __getitem__(self, attr):
        # Support int based indexing by absolute position.
        if isinstance(attr, int):
            if abs(attr) >= self.size:
                raise IndexError('Index out of range')
            index = np.unravel_index(attr % self.size, self.shape)
            return self[index]
        return np.ndarray.__getitem__(self, attr)

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
        return [_extract(v, session) for v in data]

    # Ignore leaf objects.
    if not isinstance(data, np.ndarray):
        return data

    # Convert user defined classes.
    if hasattr(data, 'classname') and session:
        cls = session._get_user_class(data.classname)
        data = cls.from_value(data)

    # Extract struct data.
    elif data.dtype.names:
        # Singular struct
        if data.size == 1:
            out = Struct()
            for name in data.dtype.names:
                item = data[name]
                # Extract values that are cells (they are doubly wrapped).
                if isinstance(item, np.ndarray) and item.dtype.kind == 'O':
                    item = item.squeeze().tolist()
                out[name] = _extract(item, session)
            data = out
        # Struct array
        else:
            data = StructArray(data, session)

    # Extract cells.
    elif data.dtype.kind == 'O':
        data = Cell(data, session)

    # Compress singleton values.
    elif data.size == 1:
        data = data.item()

    # Compress empty values.
    elif data.size == 0:
        if data.dtype.kind in 'US':
            data = ''
        else:
            data = []

    # Return parsed value.
    return data


def _encode(data, convert_to_float):
    """Convert the Python values to values suitable to send to Octave.
    """

    # Handle variable pointer.
    if isinstance(data, (OctaveVariablePtr)):
        data = data.value

    # Handle a user defined object.
    elif isinstance(data, OctaveUserClass):
        data = OctaveUserClass.to_value(data)

    # Handle a cell array.
    elif isinstance(data, Cell):
        out = np.empty(data.size, dtype=object)
        for (i, item) in enumerate(data.ravel()):
            out[i] = _encode(item, convert_to_float)
        data = out.reshape(data.shape)

    # Handle a struct array.
    elif isinstance(data, StructArray):
        out = np.empty(data.size, dtype=data.dtype)
        for (i, item) in enumerate(data.ravel()):
            for name in data.dtype.names:
                out[i][name] = _encode(item[name], convert_to_float)
        data = out.reshape(data.shape)

    # Extract the values from dict and Struct objects.
    if isinstance(data, dict):
        out = dict()
        for (key, value) in data.items():
            out[key] = _encode(value, convert_to_float)
        return out

    # Send None as nan.
    if data is None:
        return np.NaN

    # Sets are treated like lists.
    if isinstance(data, set):
        data = list(data)

    # Lists can be interpreted as numeric arrays or cell arrays.
    if isinstance(data, list):
        if _is_simple_numeric(data):
            data = np.array(data)
        else:
            data = tuple(data)

    # Tuples are handled as cells.
    if isinstance(data, tuple):
        return Cell([_encode(i, convert_to_float) for i in data])

    # Sparse data must be floating type.
    if isinstance(data, spmatrix):
        return data.astype(np.float64)

    # Return other data types unchanged.
    if not isinstance(data, np.ndarray):
        return data

    # Complex 128 is the highest supported by savemat.
    if data.dtype.name == 'complex256':
        return data.astype(np.complex128)

    # Convert to float if applicable.
    if convert_to_float and data.dtype.kind in 'ui':
        return data.astype(np.float64)

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

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
        out[key] = _extract_data(value, session)
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
    @classmethod
    def from_value(cls, value, session=None):
        """Create a struct from an Octave value and optional session.
        """
        instance = Struct()
        for name in value.dtype.names:
            data = value[name]
            if isinstance(data, np.ndarray) and data.dtype.kind == 'O':
                data = value[name].squeeze().tolist()
            instance[name] = _extract_data(data, session)
        return instance

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


class StructArray(object):
    """A Python representation of an Octave structure array.

    Notes
    =====
    Supports value access by index and accessing fields by name or value.
    Differs slightly from numpy indexing in that a single number index
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
    >>> foo.bar  # value access
    [1.0, 2.0]
    >>> foo['baz']  # item access
    [3.0, 4.0]
    >>> ell = foo[0]  # index access
    >>> foo[1]['baz']
    4.0
    """
    @classmethod
    def from_value(cls, value, session=None):
        """Create a struct array from an Octave value and optional seesion."""
        instance = StructArray()
        for i in range(value.size):
            index = np.unravel_index(i, value.shape)
            for name in value.dtype.names:
                value[index][name] = _extract_data(value[index][name], session)
        instance._value = value
        instance._session = session
        return instance

    @classmethod
    def to_value(cls, instance):
        value = instance._value
        out = np.empty(value.shape, value.dtype)
        names = instance.fieldnames
        convert_to_float = True
        if hasattr(instance, '_session'):
            convert_to_float = instance._session.convert_to_float

        for i in range(value.size):
            index = np.unravel_index(i, value.shape)
            item = out[index]
            for name in names:
                item[name] = _encode(item[name], convert_to_float)
        return out

    @property
    def fieldnames(self):
        """The field names of the struct array."""
        return self._value.dtype.names

    def __setattr__(self, attr, value):
        if attr not in ['_value', '_session'] and attr in self.fieldnames:
            self._value[attr] = value
        else:
            object.__setattr__(self, attr, value)

    def __getattr__(self, attr):
        # Access the dictionary keys for unknown attributes.
        try:
            return self[attr]
        except KeyError:
            msg = "'StructArray' object has no attribute %s" % attr
            raise AttributeError(msg)

    def __getitem__(self, attr):
        # Get an item from the struct array.
        value = self._value

        # Get the values as a nested list.
        if attr in self.fieldnames:
            return _extract_data(value[attr])

        # Support simple indexing.
        if isinstance(attr, int):
            if attr >= value.size:
                raise IndexError('Index out of range')
            index = np.unravel_index(attr, value.shape)
            return StructElement(self._value[index], self._session)

        # Otherwise use numpy indexing.
        data = value[attr]
        # Return a single value as a struct.
        if data.size == 1:
            return StructElement(data, self._session)
        instance = StructArray()
        instance._value = data
        return instance

    def __repr__(self):
        shape = self._value.shape
        if len(shape) == 1:
            shape = (shape, 1)
        msg = 'x'.join(str(i) for i in shape)
        msg += ' struct array containing the fields:'
        for key in self.fieldnames:
            msg += '\n    %s' % key
        return msg

    @property
    def __dict__(self):
        # Allow for code completion in a REPL.
        data = dict()
        for key in self.fieldnames:
            data[key] = None
        return data


class StructElement(object):
    """An element of a structure array.

    Notes
    -----
    Supports value access by index and accessing fields by name or value.
    Does not support adding or removing fields.

    This class is not meant to be directly created by the user.  It is
    created automatically for structure array values received from Octave.

    Examples
    --------
    >>> from oct2py import octave
    >>> # generate the struct array
    >>> octave.eval('foo = struct("bar", {1, 2}, "baz", {3, 4});')
    >>> foo = octave.pull('foo')
    >>> el = foo[0]
    >>> el['baz']
    3.0
    >>> el.bar = 'spam'
    >>> el.bar
    'spam'
    """

    def __init__(self, data, session=None):
        """Create a new struct element"""
        self._data = data
        self._session = session

    @classmethod
    def to_value(cls, instance):
        out = Struct()
        convert_to_float = True
        if hasattr(instance, '_session'):
            convert_to_float = instance._session.convert_to_float
        for key in instance.fieldnames:
            out[key] = _encode(instance[key], convert_to_float)
        return out

    @property
    def fieldnames(self):
        """The field names of the struct array element."""
        return self._data.dtype.names

    def __getattr__(self, attr):
        # Access the dictionary keys for unknown attributes.
        if not attr.startswith('_') and attr in self.fieldnames:
            return self.__getitem__(attr)
        return object.__getattr__(self, attr)

    def __setattr__(self, attr, value):
        if not attr.startswith('_') and attr in self.fieldnames:
            self._data[attr] = value
            return
        object.__setattr__(self, attr, value)

    def __getitem__(self, item):
        if item in self.fieldnames:
            return self._data[item]
        raise IndexError('Invalid index')

    def __setitem__(self, item, value):
        self._data[item] = value

    def __repr__(self):
        msg = 'struct array element containing the fields:'
        for key in self.fieldnames:
            msg += '\n    %s' % key
        return msg

    def __dict__(self):
        """Allow for code completion in a REPL"""
        data = dict()
        for key in self.fieldnames:
            data[key] = None
        return data


def _extract_data(data, session=None):
    # Extract each item of a list.
    if isinstance(data, list):
        return [_extract_data(v, session) for v in data]

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
            data = Struct.from_value(data, session)
        # Struct array
        else:
            data = StructArray.from_value(data, session)

    # Extract cells.
    elif data.dtype.kind == 'O':
        data = data.squeeze().tolist()
        if not isinstance(data, list):
            data = [data]
        data = _extract_data(data, session)

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
    """Convert the Python values to values suitable to sent to Octave.
    """

    # Handle variable pointer.
    if isinstance(data, (OctaveVariablePtr)):
        data = data.value

    # Handle a user defined object.
    elif isinstance(data, OctaveUserClass):
        data = OctaveUserClass.to_value(data)

    # Handle struct array.
    elif isinstance(data, StructArray):
        data = StructArray.to_value(data)

    # Handle struct element.
    elif isinstance(data, StructElement):
        data = StructElement.to_value(data)

    # Extract the values from dict and Struct objects.
    if isinstance(data, dict):
        out = dict()
        for (key, value) in data.items():
            out[key] = _encode(value, convert_to_float)
        return out

    # Send None as nan.
    if data is None:
        return np.NaN

    # Handle list-like types.
    if isinstance(data, (tuple, set, list)):
        is_tuple = isinstance(data, tuple)
        data = [_encode(o, convert_to_float) for o in data]

        if not is_tuple:
            # Convert to a numeric array if possible.
            try:
                return _handle_list(data, convert_to_float)
            except ValueError:
                pass

        # Create a cell object.
        cell = np.empty((len(data),), dtype=object)
        for i in range(len(data)):
            cell[i] = data[i]
        return cell

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


def _handle_list(data, convert_to_float):
    """Handle an encoded list."""

    # Convert to an array.
    data = np.array(data)

    # Only handle numeric types.
    if data.dtype.kind not in 'uicf':
        raise ValueError

    # Handle any other ndarray considerations.
    return _encode(data, convert_to_float)

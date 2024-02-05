"""dynamic value handling."""
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.


import types
import warnings
import weakref
from typing import Any, Dict

import numpy as np

try:
    from scipy.io.matlab import MatlabObject  # type:ignore[import-untyped]
except ImportError:
    try:  # noqa
        from scipy.io.matlab.mio5 import MatlabObject  # type:ignore[import-untyped]
    except ImportError:
        pass


class OctavePtr:
    """A pointer to an Octave workspace value."""

    def __init__(self, session_weakref, name, address):
        """Initialize the pointer."""
        self._name = name
        self._address = address
        self._ref = session_weakref
        self.__module__ = "oct2py.dynamic"
        self.__name__ = name

    @property
    def name(self):
        return self._name

    @property
    def address(self):
        return self._address


class _DocDescriptor:
    """An object that dynamically fetches the documentation
    for an Octave value.
    """

    def __init__(self, session_weakref, name):
        """Initialize the descriptor."""
        self.ref = session_weakref
        self.name = name
        self.doc = None

    def __get__(self, instance, owner=None):
        if self.doc:
            return self.doc
        self.doc = self.ref()._get_doc(self.name)
        return self.doc


class OctaveVariablePtr(OctavePtr):
    """An object that acts as a pointer to an Octave value."""

    @property
    def __doc__(self):
        return "%s is a variable" % self.name

    @property
    def value(self):
        return self._ref().pull(self.address)

    @value.setter
    def value(self, obj):
        self._ref().push(self.address, obj)


class OctaveFunctionPtr(OctavePtr):
    """An object that acts as a pointer to an Octave function."""

    def __init__(self, session_weakref, name):
        """Initialize the pointer."""
        address = "@%s" % name
        super().__init__(session_weakref, name, address)

    def __call__(self, *inputs, **kwargs):
        """Call the function."""
        # Check for allowed keyword arguments
        allowed = [
            "verbose",
            "store_as",
            "timeout",
            "stream_handler",
            "plot_dir",
            "plot_name",
            "plot_format",
            "plot_width",
            "plot_height",
            "plot_res",
            "nout",
        ]

        extras = {}
        for key, _ in kwargs.copy().items():
            if key not in allowed:
                extras[key] = kwargs.pop(key)

        if extras:
            warnings.warn("Key - value pairs are deprecated, use `func_args`", stacklevel=2)

        inputs += tuple(item for pair in extras.items() for item in pair)

        return self._ref().feval(self.name, *inputs, **kwargs)

    def __repr__(self):
        """A string repr of the pointer."""
        return '"%s" Octave function' % self.name


class OctaveUserClassAttr(OctavePtr):
    """An attribute associated with an Octave user class instance."""

    def __get__(self, instance, owner=None):
        """Get a method or property on the class."""
        if instance is None:
            return "dynamic attribute"
        pointer = OctaveUserClass.to_pointer(instance)
        return instance._ref().feval("get", pointer, self.address)

    def __set__(self, instance, value):
        """Set a method or property on the class."""
        if instance is None:
            return
        pointer = OctaveUserClass.to_pointer(instance)
        # The set function returns a new struct, so we have to store_as.
        instance._ref().feval("set", pointer, self.address, value, store_as=pointer.address)


class _MethodDocDescriptor:
    """An object that dynamically fetches the documentation
    for an Octave user class method.
    """

    def __init__(self, session_weakref, class_name, name):
        """Initialize the descriptor."""
        self.ref = session_weakref
        self.class_name = class_name
        self.name = name
        self.doc = None

    def __get__(self, instance, owner=None):
        """Get the documentation."""
        if self.doc is not None:
            return self.doc
        session = self.ref()
        class_name = self.class_name
        method = self.name
        doc = session._get_doc(f"@{class_name}/{method}")
        self.doc = doc or session._get_doc(method)
        return self.doc


class OctaveUserClassMethod(OctaveFunctionPtr):
    """A method for a user defined Octave class."""

    def __init__(self, session_weakref, name, class_name):
        """Initialize the pointer."""
        OctaveFunctionPtr.__init__(self, session_weakref, name)
        self.class_name = class_name

    def __get__(self, instance, owner=None):
        """Bind to the instance."""
        return types.MethodType(self, instance)

    def __call__(self, instance: "OctaveUserClass", *inputs: Any, **kwargs: Any) -> Any:
        """Call the class method."""
        pointer = OctaveUserClass.to_pointer(instance)
        inputs = (pointer, *inputs)
        self._ref().feval(self.name, *inputs, **kwargs)

    def __repr__(self):
        """Str repr of the pointer."""
        return f'"{self.name}" Octave method for object'


class OctaveUserClass:
    """A wrapper for an Octave user class."""

    _name: str
    _attrs: Dict[str, OctaveUserClassAttr]
    _ref: Any

    def __init__(self, *inputs, **kwargs):
        """Create a new instance with the user class constructor."""
        addr = self._address = f"{self._name}_{id(self)}"
        self._ref().feval(self._name, *inputs, store_as=addr, **kwargs)

    @classmethod
    def from_value(cls, value):
        """This is how an instance is created when we read a
        MatlabObject from a MAT file.
        """
        instance = OctaveUserClass.__new__(cls)
        instance._address = f"{instance._name}_{id(instance)}"
        instance._ref().push(instance._address, value)
        return instance

    @classmethod
    def to_value(cls, instance: "OctaveUserClass") -> MatlabObject:
        """Convert to a value to send to Octave."""
        if (
            not isinstance(instance, OctaveUserClass)  # type:ignore[redundant-expr]
            or not instance._attrs
        ):
            return {}
        # Bootstrap a MatlabObject from scipy.io
        # From https://github.com/scipy/scipy/blob/93a0ea9e5d4aba1f661b6bb0e18f9c2d1fce436a/scipy/io/matlab/mio5.py#L435-L443
        # and https://github.com/scipy/scipy/blob/93a0ea9e5d4aba1f661b6bb0e18f9c2d1fce436a/scipy/io/matlab/mio5_params.py#L224
        dtype = []
        values = []
        for attr in instance._attrs:
            dtype.append((str(attr), object))
            values.append(getattr(instance, attr))
        struct = np.array([tuple(values)], dtype)
        return MatlabObject(struct, instance._name)

    @classmethod
    def to_pointer(cls, instance):
        """Get a pointer to the private object."""
        return OctavePtr(instance._ref, instance._name, instance._address)


def _make_user_class(session, name):
    """Make an Octave class for a given class name"""
    attrs = session.eval("fieldnames(%s);" % name, nout=1).ravel().tolist()
    methods = session.eval("methods(%s);" % name, nout=1).ravel().tolist()
    ref = weakref.ref(session)

    doc = _DocDescriptor(ref, name)
    values = dict(__doc__=doc, _name=name, _ref=ref, _attrs=attrs, __module__="oct2py.dynamic")

    for method in methods:
        doc = _MethodDocDescriptor(ref, name, method)  # type:ignore[assignment]
        cls_name = f"{name}_{method}"
        method_values = dict(__doc__=doc)
        method_cls = type(str(cls_name), (OctaveUserClassMethod,), method_values)
        values[method] = method_cls(ref, method, name)

    for attr in attrs:
        values[attr] = OctaveUserClassAttr(ref, attr, attr)

    return type(str(name), (OctaveUserClass,), values)


def _make_function_ptr_instance(session, name):
    ref = weakref.ref(session)
    doc = _DocDescriptor(ref, name)
    custom = type(str(name), (OctaveFunctionPtr,), dict(__doc__=doc))
    return custom(ref, name)


def _make_variable_ptr_instance(session, name):
    """Make a pointer instance for a given variable by name."""
    return OctaveVariablePtr(weakref.ref(session), name, name)

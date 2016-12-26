import weakref
import types

from oct2py.utils import get_nout
from oct2py.compat import PY2


class OctaveFunction(object):

    def __init__(self, parent_weakref, name):
        """An object representing an Octave function.

        Methods are dynamically bound to instances of Octave objects and
        represent a callable function in the Octave session.

        Parameters
        ----------
        parent_weakref: Oct2Py instance weak reference
            A weak reference to the parent (Oct2Py instance) to which the
                OctaveFunction is being bound.
        name: str
            The name of the Octave function this represents
        """
        self.name = name
        self._ref = parent_weakref

    def __call__(self, parent, *inputs, **kwargs):
        """Call the function with the supplied arguments in the Octave session.
        """
        kwargs['nout'] = kwargs.get('nout', get_nout())
        kwargs['verbose'] = kwargs.get('verbose', False)
        return self._ref()._call(self.name, *inputs, **kwargs)

    def __repr__(self):
        return '"%s" Octave function' % self.name

    def __getattribute__(self, name):
        if name == '__doc__':
            return self._ref()._get_doc(self.name)
        return object.__getattribute__(self, name)


class OctaveClass(object):
    """A wrapper for an Octave Class.
    """

    def __init__(self, *inputs, **kwargs):
        """Create an octave class with the supplied arguments.
        """
        name = self._name
        self._var = '%s_%s' % (name, id(self))
        kwargs['nout'] = 1
        kwargs['verbose'] = kwargs.get('verbose', False)
        kwargs['_is_class'] = True
        kwargs['_class_var'] = self._var
        self._ref()._call(name, *inputs, **kwargs)
        self._create_methods()

    def _create_methods(self):
        """Create the dynamic methods.
        """
        for (name, cls) in self._methods.items():
            instance = cls(self._ref, self._var, self._name, name)
            instance.__name__ = name
            # bind to the instance.
            if PY2:
                method = types.MethodType(instance, self, OctaveClass)
            else:
                method = types.MethodType(instance, self)
            setattr(self, name, method)

    def __repr__(self):
        return '"%s" Octave class instance "%s"' % (self._name, self._var)

    def __getattribute__(self, name):
        if name == '__doc__':
            return self._ref()._get_doc(self._name)
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        if name in self._attrs:
            lookup = 'ans = get(%s, "%s");' % (self._var, name)
            return self._ref().eval(lookup)
        return object.__getattribute__(self, name)


class OctaveClassMethod(object):
    """A wrapper for an Octave class method.
    """

    def __init__(self, oct2py_weakref, var, obj_name, name):
        """An object representing an Octave class method.

        Methods are dynamically bound to instances of Octave objects and
        represent a callable function in the Octave session.

        Parameters
        ----------
        oct2py_weakref: Oct2Py instance weak reference
            A weak reference to the parent (Oct2Py instance) to which the
                OctaveClassMethod is being bound
        var: str
            The variable name of the parent instance.
        obj_name: str
            The name of the object on which the method is contained.
        name: str
            The name of the method this represents
        """
        self.name = name
        self._ref = oct2py_weakref
        self.var = var
        self._obj_name = obj_name

    def __repr__(self):
        return '"%s" method of "%s" object' % (self.name, self.var)

    def __call__(self, instance, *inputs, **kwargs):
        """Call the function with the variable name and the supplied arguments
         in the Octave session.
        """
        kwargs['nout'] = kwargs.get('nout', get_nout())
        kwargs['verbose'] = kwargs.get('verbose', False)
        kwargs['_is_class_lookup'] = True
        kwargs['_class_var'] = self.var
        return self._ref()._call(self.name, *inputs, **kwargs)

    def __getattribute__(self, name):
        if name == '__doc__':
            doc_name = '@%s/%s' % (self._obj_name, self.name)
            doc = self._ref()._get_doc(doc_name)
            return doc or self._ref()._get_doc(self.name)
        return object.__getattribute__(self, name)


def _make_octave_command(parent, name):
    """Create a wrapper to an Octave procedure or object

    Adapted from the python-matlab-bridge project
    """
    custom = type(name, (OctaveFunction,), {})
    method_instance = custom(weakref.ref(parent), name)
    method_instance.__name__ = name
    return method_instance


def _make_octave_class(parent, name):
    """Make an Octave class for a given class name"""
    attrs = parent.eval('ans = fieldnames(%s);' % name)
    methods = parent.eval('ans = methods(%s);' % name)
    values = dict()
    for attr in attrs:
        values[attr] = 'dynamic_attribute'

    def create_dynamic_method(method):
        def dynamic_method(self):
            pass
        dynamic_method.__doc__ = 'Dynamic method of "%s".' % (name)
        dynamic_method.__name__ = method
        return dynamic_method

    values['_methods'] = dict()
    for method in methods:
        values['_methods'][method] = type(method, (OctaveClassMethod,), {})
        values[method] = create_dynamic_method(method)

    values['_ref'] = weakref.ref(parent)
    values['_attrs'] = attrs
    values['_name'] = name

    custom = type(name, (OctaveClass,), values)
    custom.__module__ = 'oct2py.dynamic'
    return custom

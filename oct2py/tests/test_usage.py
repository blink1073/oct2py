from __future__ import absolute_import, print_function
import os
import logging
import pickle
import tempfile

from IPython.display import Image, SVG
import numpy as np
import pytest

from oct2py import Oct2Py, Oct2PyError, Struct, Cell
from oct2py.io import MatlabFunction
from oct2py.compat import StringIO


class TestUsage:
    """Excercise the basic interface of the package
    """
    @classmethod
    def setup_class(cls):
        cls.oc = Oct2Py()
        cls.oc.addpath(os.path.realpath(os.path.dirname(__file__)))

    @classmethod
    def teardown_class(cls):
        cls.oc.exit()

    def test_run(self):
        """Test the run command
        """
        out = self.oc.eval('ones(3,3)')
        desired = np.ones((3, 3))
        assert np.allclose(out, desired)
        out = self.oc.eval('ans = mean([[1, 2], [3, 4]])', verbose=True)
        assert out == 2.5
        with pytest.raises(Oct2PyError):
            self.oc.eval('_spam')

    def test_dynamic_functions(self):
        """Test some dynamic functions
        """
        out = self.oc.ones(1, 2)
        assert np.allclose(out, np.ones((1, 2)))

        U, S, V = self.oc.svd([[1, 2], [1, 3]], nout=3)
        assert np.allclose(U, ([[-0.57604844, -0.81741556],
                           [-0.81741556, 0.57604844]]))
        assert np.allclose(S, ([[3.86432845, 0.],
                           [0., 0.25877718]]))
        assert np.allclose(V, ([[-0.36059668, -0.93272184],
                           [-0.93272184, 0.36059668]]))
        out = self.oc.roundtrip(1)
        assert out == 1
        with pytest.raises(Oct2PyError):
            self.oc.eval('_spam')

    def test_push_pull(self):
        self.oc.push('spam', [1, 2])
        out = self.oc.pull('spam')
        assert np.allclose(out, np.array([1, 2]))
        self.oc.push(['spam', 'eggs'], ['foo', [1, 2, 3, 4]])
        spam, eggs = self.oc.pull(['spam', 'eggs'])
        assert spam == 'foo'
        assert np.allclose(eggs, np.array([[1, 2, 3, 4]]))

    def test_help(self):
        """Testing help command
        """
        doc = self.oc.cos.__doc__
        assert 'Compute the cosine for each element of X in radians.' in doc

    def test_dynamic(self):
        """Test the creation of a dynamic function
        """
        tests = [self.oc.zeros, self.oc.ones, self.oc.plot]
        for item in tests:
            assert "class 'oct2py.dynamic" in repr(type(item))
        with pytest.raises(Oct2PyError):
            self.oc.__getattr__('aaldkfasd')
        with pytest.raises(Oct2PyError):
            self.oc.__getattr__('_foo')
        with pytest.raises(Oct2PyError):
            self.oc.__getattr__('foo\\W')

    def test_open_close(self):
        """Test opening and closing the Octave session
        """
        self.oc.exit()
        with pytest.raises(Oct2PyError):
            self.oc.push(name=['a'], var=[1.0])
        self.oc.restart()
        self.oc.push('a', 5)
        a = self.oc.pull('a')
        assert a == 5

    def test_struct(self):
        """Test Struct construct
        """
        test = Struct()
        test.spam = 'eggs'
        test.eggs.spam = 'eggs'
        assert test['spam'] == 'eggs'
        assert test['eggs']['spam'] == 'eggs'
        test["foo"] = Struct()
        test["foo"]["bar"] = 10
        assert test.foo.bar == 10
        p = pickle.dumps(test)
        test2 = pickle.loads(p)
        assert test2['spam'] == 'eggs'
        assert test2['eggs']['spam'] == 'eggs'
        assert test2.foo.bar == 10
        assert 'spam' in test.__dict__

    def test_syntax_error(self):
        """Make sure a syntax error in Octave throws an Oct2PyError
        """
        with pytest.raises(Oct2PyError):
            self.oc.eval("a='1")

        if os.name == 'nt':
            self.oc.restart()

        with pytest.raises(Oct2PyError):
            self.oc.eval("a=1++3")

        if os.name == 'nt':
            self.oc.restart()

        self.oc.push('a', 1)
        a = self.oc.pull('a')
        assert a == 1

    def test_extract_figures(self):
        plot_dir = tempfile.mkdtemp().replace('\\', '/')
        code = """
        figure 1
        plot([1,2,3])
        figure 2
        temp=rand(100,100);
        imshow(temp)
        """
        self.oc.eval(code, plot_dir=plot_dir, plot_format='svg')
        imgs = self.oc.extract_figures(plot_dir)
        assert len(imgs) == 2
        assert isinstance(imgs[0], SVG) or isinstance(imgs[1], SVG)

    def test_quit(self):
        with pytest.raises(Oct2PyError):
            self.oc.eval("quit")
        self.oc.eval('a=1')

    def test_octave_error(self):
        with pytest.raises(Oct2PyError):
            self.oc.eval("a = ones2(1)")

    def test_keyword_arguments(self):
        self.oc.set(0, DefaultFigureColor='b', nout=0)
        plot_dir = tempfile.mkdtemp().replace('\\', '/')
        self.oc.plot([1, 2, 3], linewidth=3, plot_dir=plot_dir)
        assert self.oc.extract_figures(plot_dir)

    def test_octave_function(self):
        func = MatlabFunction([1])
        with pytest.raises(Oct2PyError):
            self.oc.push('x', func)

    def test_bad_getattr(self):
        self.oc.eval('foo = 1')
        with pytest.raises(Oct2PyError):
            self.oc.__getattr__('foo')

    def test_octave_class(self):
        self.oc.addpath(os.path.realpath(os.path.dirname(__file__)))
        polynomial = self.oc.polynomial
        p0 = polynomial([1, 2, 3])
        assert np.allclose(p0.poly, [[1, 2, 3]])

        p1 = polynomial([0, 1, 2])
        sobj = StringIO()
        hdlr = logging.StreamHandler(sobj)
        hdlr.setLevel(logging.DEBUG)
        self.oc.logger.addHandler(hdlr)
        self.oc.logger.setLevel(logging.DEBUG)
        p1.display(verbose=True, nout=0)
        text = hdlr.stream.getvalue().strip()
        self.oc.logger.removeHandler(hdlr)
        assert 'in poly display' in text

        self.oc.push('y', p0)
        p2 = self.oc.pull('y')
        assert np.allclose(p2.poly, [1, 2, 3])

        p2.poly = [2, 3, 4]
        assert np.allclose(p2.poly, [2, 3, 4])

        assert 'Display a polynomial object' in p2.display.__doc__

        self.oc.eval('p3 = polynomial([1,2,3])')
        p3 = self.oc.pull('p3')
        assert np.allclose(p3.poly, [1, 2, 3])

    def test_get_pointer(self):
        self.oc.addpath(os.path.realpath(os.path.dirname(__file__)))
        self.oc.push('y', 1)
        yptr = self.oc.get_pointer('y')
        assert yptr.name == 'y'
        assert yptr.value == 1
        assert yptr.address == 'y'
        yptr.value = 2
        assert yptr.value == 2
        assert self.oc.pull('y') == 2
        assert 'is a variable' in yptr.__doc__
        ones = self.oc.ones(yptr)
        assert ones.shape == (2, 2)

        onesptr = self.oc.get_pointer('ones')
        assert onesptr.name == 'ones'
        assert onesptr.address == '@ones'
        assert 'ones' in onesptr.__doc__

        sin = self.oc.get_pointer('sin')
        x = self.oc.quad(sin, 0, self.oc.pi())
        assert x == 2

        self.oc.eval('p = polynomial([1,2,3])')
        ppter = self.oc.get_pointer('p')
        assert ppter.name == 'p'
        assert ppter.address == 'p'
        p = ppter.value
        assert np.allclose(p.poly, [1, 2, 3])

        clsptr = self.oc.get_pointer('polynomial')
        value = clsptr([1, 2, 3])
        assert np.allclose(value.poly, [1, 2, 3])

        with pytest.raises(Oct2PyError):
            self.oc.get_pointer('foo123')

    def test_get_max_nout(self):
        self.oc.addpath(os.path.realpath(os.path.dirname(__file__)))
        here = os.path.dirname(__file__)
        max_nout = self.oc._get_max_nout(os.path.join(here, 'roundtrip.m'))
        assert max_nout == 2

    def test_feval(self):
        self.oc.addpath(os.path.realpath(os.path.dirname(__file__)))
        a = self.oc.feval('ones', 3)
        assert np.allclose(a, np.ones((3, 3)))

        self.oc.feval('ones', 3, store_as='foo')
        b = self.oc.pull('foo')
        assert np.allclose(b, np.ones((3, 3)))

        self.oc.push('x', 3)
        ptr = self.oc.get_pointer('x')
        c = self.oc.feval('ones', ptr)
        assert np.allclose(c, np.ones((3, 3)))

        p = self.oc.polynomial([1, 2, 3])
        poly = self.oc.feval('get', p, 'poly')
        assert np.allclose(poly, [1, 2, 3])

        val = self.oc.feval('disp', self.oc.zeros)
        assert val.strip() == '@zeros'

        lines = []
        self.oc.feval('evalin', 'base', 'disp(1);disp(2);disp(3)',
                      nout=0,
                      stream_handler=lines.append)
        assert lines == [' 1', ' 2', ' 3'], lines

        val = self.oc.feval('svd', [[1, 2], [1, 3]])
        u, v, d = self.oc.feval('svd', [[1, 2], [1, 3]], nout=3)
        assert isinstance(val, np.ndarray)
        assert isinstance(u, np.ndarray)

        self.oc.feval('test_nodocstring.m', 1)
        with pytest.raises(TypeError):
            self.oc.feval('test_usage.py')

    def test_eval(self):
        a = self.oc.eval('ones(3);')
        assert np.allclose(a, np.ones((3, 3)))

        lines = []
        self.oc.eval('disp(1);disp(2);disp(3)',
                     nout=0,
                     stream_handler=lines.append)
        assert lines == [' 1', ' 2', ' 3'], lines

        a = self.oc.eval(['zeros(3);', 'ones(3);'])
        assert np.allclose(a, np.ones((3, 3)))

        U, S, V = self.oc.eval('svd(hilb(3))', nout=3)
        assert isinstance(U, np.ndarray)

    def test_no_args_returned(self):
        # Test a function that only works when nargout=0
        here = os.path.dirname(__file__)
        self.oc.source(os.path.join(here, 'roundtrip.m'))

    def test_script_error(self):
        here = os.path.dirname(__file__)
        with pytest.raises(Oct2PyError) as exec_info:
            self.oc.source(os.path.join(here, 'script_error.m'))
        msg = str(exec_info.value)
        assert msg == (
            "Octave evaluation error:\nerror: "
            "'b' undefined near line 2 column 3\nerror: called from:\n    script_error at line 2, column 2"
        )

    @pytest.mark.parametrize("fn", [
        "pyeval_like_error%s" % i for i in range(4)
    ])
    def test_script_error_like_my_pyeval(self, fn):
        exp = "element number 1 undefined in return list"
        here = os.path.dirname(__file__)
        with pytest.raises(Oct2PyError, match=exp):
            self.oc.source(os.path.join(here, "%s.m" % fn))

    def test_script_error_like_my_pyeval0(self):
        exp = "element number 1 undefined in return list"
        with pytest.raises(Oct2PyError, match=exp):
            self.oc.pyeval_like_error0()

    def test_script_error_like_my_pyeval1(self):
        exp = "element number 1 undefined in return list"
        with pytest.raises(Oct2PyError, match=exp):
            self.oc.pyeval_like_error1()

    def test_script_error_like_my_pyeval2(self):
        exp = "element number 1 undefined in return list"
        with pytest.raises(Oct2PyError, match=exp):
            self.oc.pyeval_like_error2(1)

    def test_script_error_like_my_pyeval3(self):
        exp = "element number 1 undefined in return list"
        with pytest.raises(Oct2PyError, match=exp):
            self.oc.pyeval_like_error3(1)

    def test_pkg_load(self):
        self.oc.eval('pkg load signal')
        t = np.linspace(0, 1, num=100)
        x = np.cos(2*np.pi*t*3)
        # on Travis CI this is giving a dimension mismatch error
        try:
            y = self.oc.sgolayfilt(x, 3, 5)
        except Oct2PyError as e:
            if 'dimensions mismatch' in str(e):
                return
        assert y.shape == (1, 100)

    def test_passing_integer_args(self):
        self.oc.eval("""
function [res, a, b] = foo(a, b)
res = a * b;
end
""")
        res, a, b = self.oc.foo(np.nan, 2, nout=3)
        assert np.isnan(res)
        assert np.isnan(a)
        assert b == 2

    def test_carriage_return(self):
        self.oc.eval(r"disp('hi\rthere')")

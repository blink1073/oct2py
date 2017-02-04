from __future__ import absolute_import, print_function
import os
import logging
import pickle
import tempfile

from IPython.display import Image, SVG
import numpy as np
import numpy.testing as test


from oct2py import Oct2Py, Oct2PyError
from oct2py.utils import Struct
from oct2py.compat import StringIO


class BasicUsageTest(test.TestCase):
    """Excercise the basic interface of the package
    """
    def setUp(self):
        self.oc = Oct2Py()
        self.oc.addpath(self.oc.genpath(os.path.dirname(__file__)))

    def tearDown(self):
        self.oc.exit()

    def test_run(self):
        """Test the run command
        """
        out = self.oc.eval('ones(3,3)')
        desired = np.ones((3, 3))
        test.assert_allclose(out, desired)
        out = self.oc.eval('ans = mean([[1, 2], [3, 4]])', verbose=True)
        self.assertEqual(out, 2.5)
        self.assertRaises(Oct2PyError, self.oc.eval, '_spam')

    def test_dynamic_functions(self):
        """Test some dynamic functions
        """
        out = self.oc.ones(1, 2)
        assert np.allclose(out, np.ones((1, 2)))
        U, S, V = self.oc.svd([[1, 2], [1, 3]])
        assert np.allclose(U, ([[-0.57604844, -0.81741556],
                           [-0.81741556, 0.57604844]]))
        assert np.allclose(S,  ([[3.86432845, 0.],
                           [0., 0.25877718]]))
        assert np.allclose(V,  ([[-0.36059668, -0.93272184],
                           [-0.93272184, 0.36059668]]))
        out = self.oc.roundtrip(1)
        self.assertEqual(out, 1)
        self.assertEqual(out, 1)
        self.assertRaises(Oct2PyError, self.oc.eval, '_spam')

    def test_push_pull(self):
        self.oc.push('spam', [1, 2])
        out = self.oc.pull('spam')
        assert np.allclose(out, np.array([1, 2]))
        self.oc.push(['spam', 'eggs'], ['foo', [1, 2, 3, 4]])
        spam, eggs = self.oc.pull(['spam', 'eggs'])
        self.assertEqual(spam, 'foo')
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
        self.assertRaises(Oct2PyError, self.oc.__getattr__, 'aaldkfasd')
        self.assertRaises(Oct2PyError, self.oc.__getattr__, '_foo')
        self.assertRaises(Oct2PyError, self.oc.__getattr__, 'foo\W')

    def test_open_close(self):
        """Test opening and closing the Octave session
        """
        self.oc.exit()
        self.assertRaises(Oct2PyError, self.oc.push, name=['a'],
                          var=[1.0])
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
        self.assertEqual(test['spam'], 'eggs')
        self.assertEqual(test['eggs']['spam'], 'eggs')
        test["foo"]["bar"] = 10
        self.assertEqual(test.foo.bar, 10)
        p = pickle.dumps(test)
        test2 = pickle.loads(p)
        self.assertEqual(test2['spam'], 'eggs')
        self.assertEqual(test2['eggs']['spam'], 'eggs')
        self.assertEqual(test2.foo.bar, 10)

    def test_syntax_error(self):
        """Make sure a syntax error in Octave throws an Oct2PyError
        """
        self.assertRaises(Oct2PyError, self.oc.eval, "a='1")

        if os.name == 'nt':
            self.oc.restart()

        self.assertRaises(Oct2PyError, self.oc.eval, "a=1++3")

        if os.name == 'nt':
            self.oc.restart()

        self.oc.push('a', 1)
        a = self.oc.pull('a')
        self.assertEqual(a, 1)

    def test_extract_figures(self):
        plot_dir = tempfile.mkdtemp().replace('\\', '/')
        code = """
        plot([1,2,3])
        figure
        temp=rand(100,100);
        imshow(temp)
        """
        self.oc.eval(code, plot_dir=plot_dir)
        files = self.oc.extract_figures(plot_dir)
        assert len(files) == 2
        assert isinstance(files[0], SVG)
        assert isinstance(files[1], Image)

    def test_quit(self):
        self.assertRaises(Oct2PyError, self.oc.eval, 'quit')
        self.oc.eval('a=1')

    def test_octave_error(self):
        self.assertRaises(Oct2PyError, self.oc.eval, 'a = ones2(1)')

    def test_keyword_arguments(self):
        self.oc.set(0, DefaultFigureColor='b')
        plot_dir = tempfile.mkdtemp().replace('\\', '/')
        self.oc.plot([1, 2, 3], linewidth=3, plot_dir=plot_dir)
        assert self.oc.extract_figures(plot_dir)

    def test_octave_class(self):
        polynomial = self.oc.polynomial
        p0 = polynomial([1, 2, 3])
        test.assert_equal(p0.poly, [[1, 2, 3]])

        p1 = polynomial([0, 1, 2])
        sobj = StringIO()
        hdlr = logging.StreamHandler(sobj)
        hdlr.setLevel(logging.DEBUG)
        self.oc.logger.addHandler(hdlr)
        self.oc.logger.setLevel(logging.DEBUG)
        p1.display(verbose=True)
        text = hdlr.stream.getvalue().strip()
        self.oc.logger.removeHandler(hdlr)
        assert 'X + 2 * X ^ 2' in text

        self.oc.push('y', p0)
        p2 = self.oc.pull('y')
        assert np.allclose(p2.poly, [1, 2, 3])

    def test_get_pointer(self):
        self.oc.push('y', 1)
        yptr = self.oc.get_pointer('y')
        assert yptr.name == 'y'
        assert yptr.value == 1
        assert yptr.address == 'y'

        onesptr = self.oc.get_pointer('ones')
        assert onesptr.name == 'ones'
        assert onesptr.address == '@ones'

        self.oc.eval('p = polynomial([1,2,3])')
        ppter = self.oc.get_pointer('p')
        assert ppter.name == 'p'
        assert ppter.address == 'p'
        p = ppter.value
        assert np.allclose(p.poly, [1, 2, 3])

        clsptr = self.oc.get_pointer('polynomial')
        value = clsptr([1, 2, 3])
        assert np.allclose(value.poly, [1, 2, 3])

        self.assertRaises(Oct2PyError, self.oc.get_pointer, 'foo')

    def test_feval(self):
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
        val2 = self.oc.feval('svd', [[1, 2], [1, 3]], nout=3)
        assert isinstance(val, np.ndarray)
        assert isinstance(val2, list)
        assert len(val2), 3

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

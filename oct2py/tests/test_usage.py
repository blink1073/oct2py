from __future__ import absolute_import, print_function
import glob
import os
import pickle
import tempfile

import numpy as np
import numpy.testing as test


from oct2py import Oct2Py, Oct2PyError
from oct2py.utils import Struct


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
        self.assertRaises(Oct2PyError, self.oc.push, '_spam', 1)

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
            try:
                self.assertEqual(repr(type(item)), "<type 'function'>")
            except AssertionError:
                self.assertEqual(repr(type(item)), "<class 'function'>")
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

    def test_octave_error(self):
        self.assertRaises(Oct2PyError, self.oc.eval, 'a = ones2(1)')

    def test_keyword_arguments(self):
        self.oc.set(0, DefaultFigureColor='b')
        plot_dir = tempfile.mkdtemp().replace('\\', '/')
        self.oc.plot([1, 2, 3], linewidth=3, plot_dir=plot_dir)
        self.oc.close()
        assert glob.glob("%s/*" % plot_dir)

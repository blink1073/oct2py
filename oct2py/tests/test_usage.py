from __future__ import absolute_import, print_function
import os
import pickle

import numpy as np
import numpy.testing as test


from oct2py import Oct2Py, Oct2PyError
from oct2py.utils import Struct


class BasicUsageTest(test.TestCase):
    """Excercise the basic interface of the package
    """
    def setUp(self):
        self.oc = Oct2Py()
        self.oc.addpath(os.path.dirname(__file__))

    def test_run(self):
        """Test the run command
        """
        out = self.oc.run('y=ones(3,3)')
        desired = """y =

        1        1        1
        1        1        1
        1        1        1
"""
        self.assertEqual(out, desired)
        out = self.oc.run('x = mean([[1, 2], [3, 4]])', verbose=True)
        self.assertEqual(out, 'x =  2.5000')
        self.assertRaises(Oct2PyError, self.oc.run, '_spam')

    def test_call(self):
        """Test the call command
        """
        out = self.oc.call('ones', 1, 2)
        assert np.allclose(out, np.ones((1, 2)))
        U, S, V = self.oc.call('svd', [[1, 2], [1, 3]])
        assert np.allclose(U, ([[-0.57604844, -0.81741556],
                           [-0.81741556, 0.57604844]]))
        assert np.allclose(S,  ([[3.86432845, 0.],
                           [0., 0.25877718]]))
        assert np.allclose(V,  ([[-0.36059668, -0.93272184],
                           [-0.93272184, 0.36059668]]))
        out = self.oc.call('roundtrip.m', 1)
        self.assertEqual(out, 1)
        fname = os.path.join(__file__, 'roundtrip.m')
        out = self.oc.call(fname, 1)
        self.assertEqual(out, 1)
        self.assertRaises(Oct2PyError, self.oc.call, '_spam')

    def test_put_get(self):
        """Test putting and getting values
        """
        self.oc.put('spam', [1, 2])
        out = self.oc.get('spam')
        assert np.allclose(out, np.array([1, 2]))
        self.oc.put(['spam', 'eggs'], ['foo', [1, 2, 3, 4]])
        spam, eggs = self.oc.get(['spam', 'eggs'])
        self.assertEqual(spam, 'foo')
        assert np.allclose(eggs, np.array([[1, 2, 3, 4]]))
        self.assertRaises(Oct2PyError, self.oc.put, '_spam', 1)
        self.assertRaises(Oct2PyError, self.oc.get, '_spam')

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
        oct_ = Oct2Py()
        oct_.close()
        self.assertRaises(Oct2PyError, oct_.put, names=['a'],
                          var=[1.0])
        oct_.restart()
        oct_.put('a', 5)
        a = oct_.get('a')
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
        oc = Oct2Py()
        self.assertRaises(Oct2PyError, oc._eval, "a='1")
        oc = Oct2Py()
        self.assertRaises(Oct2PyError, oc._eval, "a=1++3")

        oc.put('a', 1)
        a = oc.get('a')
        self.assertEqual(a, 1)

    def test_octave_error(self):
        oc = Oct2Py()
        self.assertRaises(Oct2PyError, oc.run, 'a = ones2(1)')

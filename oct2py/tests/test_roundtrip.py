from __future__ import absolute_import, print_function
import os

import numpy as np
import numpy.testing as test


from oct2py import Oct2Py, Oct2PyError
from oct2py.utils import Struct
from oct2py.compat import unicode, long


TYPE_CONVERSIONS = [
    (int, 'int32', np.int32),
    (long, 'int64', np.int64),
    (float, 'double', np.float64),
    (complex, 'double', np.complex128),
    (str, 'char', unicode),
    (unicode, 'cell', unicode),
    (bool, 'int8', np.int8),
    (None, 'double', np.float64),
    (dict, 'struct', Struct),
    (np.int8, 'int8', np.int8),
    (np.int16, 'int16', np.int16),
    (np.int32, 'int32', np.int32),
    (np.int64, 'int64', np.int64),
    (np.uint8, 'uint8', np.uint8),
    (np.uint16, 'uint16', np.uint16),
    (np.uint32, 'uint32', np.uint32),
    (np.uint64, 'uint64', np.uint64),
    #(np.float16, 'double', np.float64),
    (np.float32, 'double', np.float64),
    (np.float64, 'double', np.float64),
    (np.str, 'char', np.unicode),
    (np.double, 'double', np.float64),
    (np.complex64, 'double', np.complex128),
    (np.complex128, 'double', np.complex128),
]


class RoundtripTest(test.TestCase):
    """Test roundtrip value and type preservation between Python and Octave.

    Uses test_datatypes.m to read in a dictionary with all Octave types
    uses roundtrip.m to send each of the values out and back,
        making sure the value and the type are preserved.

    """
    @classmethod
    def setUpClass(cls):
        cls.oc = Oct2Py()
        cls.oc.addpath(os.path.dirname(__file__))
        cls.data = cls.oc.test_datatypes()

    @classmethod
    def tearDownClass(cls):
        cls.oc.exit()

    def nested_equal(self, val1, val2):
        """Test for equality in a nested list or ndarray
        """
        if isinstance(val1, list):
            for (subval1, subval2) in zip(val1, val2):
                if isinstance(subval1, list):
                    self.nested_equal(subval1, subval2)
                elif isinstance(subval1, np.ndarray):
                    np.allclose(subval1, subval2)
                else:
                    self.assertEqual(subval1, subval2)
        elif isinstance(val1, np.ndarray):
            np.allclose(val1, np.array(val2))
        elif isinstance(val1, (str, unicode)):
            self.assertEqual(val1, val2)
        else:
            try:
                assert (np.alltrue(np.isnan(val1)) and
                        np.alltrue(np.isnan(val2)))
            except (AssertionError, NotImplementedError):
                self.assertEqual(val1, val2)

    def helper(self, outgoing, expected_type=None):
        """
        Use roundtrip.m to make sure the data goes out and back intact.

        Parameters
        ==========
        outgoing : object
            Object to send to Octave.

        """
        incoming = self.oc.roundtrip(outgoing)
        if expected_type is None:
            expected_type = type(outgoing)
        self.nested_equal(incoming, outgoing)
        try:
            self.assertEqual(type(incoming), expected_type)
        except AssertionError:
            if type(incoming) == np.float32 and expected_type == np.float64:
                pass

    def test_int(self):
        """Test roundtrip value and type preservation for integer types
        """
        for key in ['int8', 'int16', 'int32', 'int64',
                    'uint8', 'uint16', 'uint32', 'uint64']:
            self.helper(self.data.num.int[key])

    def test_float(self):
        """Test roundtrip value and type preservation for float types
        """
        for key in ['float64', 'complex', 'complex_matrix']:
            self.helper(self.data.num[key])
        self.helper(self.data.num['float32'], np.float64)

    def test_misc_num(self):
        """Test roundtrip value and type preservation for misc numeric types
        """
        for key in ['inf', 'NaN', 'matrix', 'vector', 'column_vector',
                    'matrix3d', 'matrix5d']:
            self.helper(self.data.num[key])

    def test_logical(self):
        """Test roundtrip value and type preservation for logical type
        """
        self.helper(self.data.logical)

    def test_string(self):
        """Test roundtrip value and type preservation for string types
        """
        for key in ['basic', 'cell_array']:
            self.helper(self.data.string[key])

    def test_struct_array(self):
        """Test roundtrip value and type preservation for struct array types
        """
        self.helper(self.data.struct_array['name'])
        self.helper(self.data.struct_array['age'], np.ndarray)

    def test_cell_array(self):
        """Test roundtrip value and type preservation for cell array types
        """
        for key in ['vector', 'matrix', 'array']:
            self.helper(self.data.cell[key])
        #self.helper(DATA.cell['array'], np.ndarray)

    def test_octave_origin(self):
        '''Test all of the types, originating in octave, and returning
        '''
        self.oc.eval('x = test_datatypes();')
        assert self.oc.pull('x') is not None
        self.oc.push('y', self.data)
        try:
            self.oc.isequaln
            func = 'isequaln'
        except Oct2PyError:
            func = 'isequalwithequalnans'
        for key in self.data.keys():
            if key not in ['struct_array', 'num', 'mixed']:
                cmd = '{0}(x.{1},y.{1})'.format(func, key)
                assert self.oc.eval(cmd), key
        self.oc.convert_to_float = False
        self.oc.push('y', self.data)
        cmd = '%s(x.num,y.num)' % func
        assert self.oc.eval(cmd), cmd
        self.oc.convert_to_float = True


class BuiltinsTest(test.TestCase):
    """Test the exporting of standard Python data types, checking their type.

    Runs roundtrip.m and tests the types of all the values to make sure they
    were brought in properly.

    """
    @classmethod
    def setUpClass(cls):
        cls.oc = Oct2Py()
        cls.oc.addpath(os.path.dirname(__file__))

    @classmethod
    def tearDownClass(cls):
        cls.oc.exit()

    def helper(self, outgoing, incoming=None, expected_type=None):
        """
        Uses roundtrip.m to make sure the data goes out and back intact.

        Parameters
        ==========
        outgoing : object
            Object to send to Octave
        incoming : object, optional
            Object already retreived from Octave

        """
        if incoming is None:
            incoming = self.oc.roundtrip(outgoing)
        if not expected_type:
            for out_type, _, in_type in TYPE_CONVERSIONS:
                if out_type == type(outgoing):
                    expected_type = in_type
                    break
        if not expected_type:
            expected_type = np.ndarray
        try:
            self.assertEqual(incoming, outgoing)
        except ValueError:
            assert np.allclose(np.array(incoming), np.array(outgoing))
        if type(incoming) != expected_type:
            incoming = self.oc.roundtrip(outgoing)
            assert expected_type(incoming) == incoming

    def test_dict(self):
        """Test python dictionary
        """
        test = dict(x='spam', y=[1, 2, 3])
        incoming = self.oc.roundtrip(test)
        #incoming = dict(incoming)
        for key in incoming:
            self.helper(test[key], incoming[key])

    def test_nested_dict(self):
        """Test nested python dictionary
        """
        test = dict(x=dict(y=1e3, z=[1, 2]), y='spam')
        incoming = self.oc.roundtrip(test)
        incoming = dict(incoming)
        for key in test:
            if isinstance(test[key], dict):
                for subkey in test[key]:
                    self.helper(test[key][subkey], incoming[key][subkey])
            else:
                self.helper(test[key], incoming[key])

    def test_set(self):
        """Test python set type
        """
        test = set((1, 2, 3, 3))
        incoming = self.oc.roundtrip(test)
        assert np.allclose(tuple(test), incoming)
        self.assertEqual(type(incoming), np.ndarray)

    def test_tuple(self):
        """Test python tuple type
        """
        test = tuple((1, 2, 3))
        self.helper(test, expected_type=np.ndarray)

    def test_list(self):
        """Test python list type
        """
        tests = [[1, 2], ['a', 'b']]
        self.helper(tests[0])
        self.helper(tests[1], expected_type=list)

    def test_list_of_tuples(self):
        """Test python list of tuples
        """
        test = [(1, 2), (1.5, 3.2)]
        self.helper(test)

    def test_numeric(self):
        """Test python numeric types
        """
        test = np.random.randint(1000)
        self.helper(int(test))
        self.helper(long(test))
        self.helper(float(test))
        self.helper(complex(1, 2))

    def test_string(self):
        """Test python str and unicode types
        """
        tests = ['spam', unicode('eggs')]
        for t in tests:
            self.helper(t)

    def test_nested_list(self):
        """Test python nested lists
        """
        test = [['spam', 'eggs'], ['foo ', 'bar ']]
        self.helper(test, expected_type=list)
        test = [[1, 2], [3, 4]]
        self.helper(test)
        test = [[1, 2], [3, 4, 5]]
        incoming = self.oc.roundtrip(test)
        for i in range(len(test)):
            assert np.alltrue(incoming[i] == np.array(test[i]))

    def test_bool(self):
        """Test boolean values
        """
        tests = (True, False)
        for t in tests:
            incoming = self.oc.roundtrip(t)
            self.assertEqual(incoming, t)
            self.assertEqual(incoming.dtype, np.dtype('float64'))
            self.oc.convert_to_float = False
            incoming = self.oc.roundtrip(t)
            self.assertEqual(incoming, t)
            self.assertEqual(incoming.dtype, np.dtype('int8'))
            self.oc.convert_to_float = True

    def test_none(self):
        """Test sending None type
        """
        incoming = self.oc.roundtrip(None)
        assert np.isnan(incoming)

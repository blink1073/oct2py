from __future__ import absolute_import, print_function
import os

import numpy as np
import numpy.testing as test


from oct2py import Oct2Py
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


class ConversionTest(test.TestCase):
    """Test the importing of all Octave data types, checking their type

    Uses test_datatypes.m to read in a dictionary with all Octave types
    Tests the types of all the values to make sure they were
        brought in properly.

    """
    @classmethod
    def setUpClass(cls):
        cls.oc = Oct2Py()
        cls.oc.addpath(os.path.dirname(__file__))
        cls.data = cls.oc.test_datatypes()

    @classmethod
    def tearDownClass(cls):
        cls.oc.exit()

    def helper(self, base, keys, types):
        """
        Perform type checking of the values

        Parameters
        ==========
        base : dict
            Sub-dictionary we are accessing.
        keys : array-like
            List of keys to test in base.
        types : array-like
            List of expected return types for the keys.

        """
        for key, type_ in zip(keys, types):
            if not type(base[key]) == type_:
                try:
                    assert type_(base[key]) == base[key]
                except ValueError:
                    assert np.allclose(type_(base[key]), base[key])

    def test_int(self):
        """Test incoming integer types
        """
        keys = ['int8', 'int16', 'int32', 'int64',
                'uint8', 'uint16', 'uint32', 'uint64']
        types = [np.int8, np.int16, np.int32, np.int64,
                 np.uint8, np.uint16, np.uint32, np.uint64]
        self.helper(self.data.num.int, keys, types)

    def test_floats(self):
        """Test incoming float types
        """
        keys = ['float32', 'float64', 'complex', 'complex_matrix']
        types = [np.float64, np.float64, np.complex128, np.ndarray]
        self.helper(self.data.num, keys, types)
        self.assertEqual(self.data.num.complex_matrix.dtype,
                         np.dtype('complex128'))

    def test_misc_num(self):
        """Test incoming misc numeric types
        """
        keys = ['inf', 'NaN', 'matrix', 'vector', 'column_vector', 'matrix3d',
                'matrix5d']
        types = [np.float64, np.float64, np.ndarray, np.ndarray, np.ndarray,
                 np.ndarray, np.ndarray]
        self.helper(self.data.num, keys, types)

    def test_logical(self):
        """Test incoming logical type
        """
        self.assertEqual(type(self.data.logical), np.ndarray)

    def test_string(self):
        """Test incoming string types
        """
        keys = ['basic', 'char_array', 'cell_array']
        types = [unicode, list, list]
        self.helper(self.data.string, keys, types)

    def test_struct_array(self):
        ''' Test incoming struct array types '''
        keys = ['name', 'age']
        types = [list, list]
        self.helper(self.data.struct_array, keys, types)

    def test_cell_array(self):
        ''' Test incoming cell array types '''
        keys = ['vector', 'matrix']
        types = [list, list]
        self.helper(self.data.cell, keys, types)

    def test_mixed_struct(self):
        '''Test mixed struct type
        '''
        keys = ['array', 'cell', 'scalar']
        types = [list, list, float]
        self.helper(self.data.mixed, keys, types)

    def test_python_conversions(self):
        """Test roundtrip python type conversions
        """
        self.oc.addpath(os.path.dirname(__file__))
        for out_type, oct_type, in_type in TYPE_CONVERSIONS:
            if out_type == dict:
                outgoing = dict(x=1)
            elif out_type is None:
                outgoing = None
            else:
                outgoing = out_type(1)
            incoming, octave_type = self.oc.roundtrip(outgoing)
            if octave_type == 'int32' and oct_type == 'int64':
                pass
            elif octave_type == 'char' and oct_type == 'cell':
                pass
            elif octave_type == 'single' and oct_type == 'double':
                pass
            elif octave_type == 'int64' and oct_type == 'int32':
                pass
            else:
                assert (octave_type == oct_type or
                        (octave_type == 'double' and self.oc.convert_to_float))
            if type(incoming) != in_type:
                if type(incoming) == np.int32 and in_type == np.int64:
                    pass
                else:
                    assert in_type(incoming) == incoming

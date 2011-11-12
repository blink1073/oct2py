''' py2oct_test - Test value passing between python and octave

Uses test_datatypes.m to read in a dictionary with all Matlab types
OctaveIncomingTest tests the types of all the values to make sure they were
brought in properly.
OctaveRoundtripTest uses roundtrip.m to send each of the values out and back,
making sure the value and the type are preserved.
'''
import unittest
import numpy as np
from py2oct import Octave


class OctaveRoundtripTest(unittest.TestCase):
    ''' Test roundtrip value and type preservation between Python and Octave

    Uses test_datatypes.m to read in a dictionary with all Matlab types
    uses roundtrip.m to send each of the values out and back,
        making sure the value and the type are preserved.
    '''
    def setUp(self):
        ''' Open an instance of Octave and get a struct with all
             of the datatypes
        '''
        self.octave = Octave()
        self.data = self.octave.test_datatypes()

    def helper(self, outgoing):
        ''' Uses roundtrip.m to make sure the data goes out
            and comes back intact
        '''
        incoming = self.octave.roundtrip(outgoing)
        try:
            self.assertEqual(incoming, outgoing)
            self.assertEqual(type(incoming), type(outgoing))
        except ValueError:
            # np arrays must be compared specially
            assert np.allclose(incoming, outgoing)
        except AssertionError:
            # need to test for NaN explicitly
            if np.isnan(outgoing) and np.isnan(incoming):
                pass
            # floats are converted to doubles by Matlab
            elif (type(outgoing) == np.float32 and
                  type(incoming) == np.float64):
                pass
            else:
                raise

    def test_int(self):
        ''' Test roundtrip value and type preservation for integer types '''
        for key in ['int8', 'int16', 'int32', 'int64',
                    'uint8', 'uint16', 'uint32', 'uint64']:
            self.helper(self.data.num.int[key])

    def test_float(self):
        ''' Test roundtrip value and type preservation for float types '''
        for key in ['float32', 'float64', 'complex', 'complex_matrix']:
            self.helper(self.data.num[key])

    def test_misc_num(self):
        ''' Test roundtrip value and type preservation for misc numeric types
        '''
        for key in ['inf', 'NaN', 'matrix', 'vector', 'column_vector',
                    'matrix3d']:
            self.helper(self.data.num[key])

    def test_logical(self):
        ''' Test roundtrip value and type preservation for logical type '''
        self.helper(self.data.logical)

    def test_string(self):
        ''' Test roundtrip value and type preservation for string types '''
        for key in ['basic', 'cell_array']:
            self.helper(self.data.string[key])

    def test_struct(self):
        ''' Test roundtrip value and type preservation for struct types '''
        for key in ['name', 'age']:
            self.helper(self.data.struct.array[key])

    def test_cell_array(self):
        ''' Test roundtrip value and type preservation for cell array types
        '''
        # XXX Not implemented
        pass
        #for key in ['vector', 'matrix']:
            #self.helper(self.data.cell[key])


class OctaveIncomingTest(unittest.TestCase):
    ''' Test the importing of all Matlab data types, checking their type

    Uses test_datatypes.m to read in a dictionary with all Matlab types
    Tests the types of all the values to make sure they were
        brought in properly.
    '''
    def setUp(self):
        ''' Open an instance of Octave and get a struct with all of the
            datatypes
        '''
        self.octave = Octave()
        self.data = self.octave.test_datatypes()

    def helper(self, base, keys, types):
        ''' Performs the actual type checking of the values '''
        for key, type_ in zip(keys, types):
            self.assertEqual(type(base[key]), type_)

    def test_int(self):
        ''' Test incoming integer types '''
        keys = ['int8', 'int16', 'int32', 'int64',
                    'uint8', 'uint16', 'uint32', 'uint64']
        types = [np.int8, np.int16, np.int32, np.int64,
                    np.uint8, np.uint16, np.uint32, np.uint64]
        self.helper(self.data.num.int, keys, types)

    def test_floats(self):
        ''' Test incoming float types '''
        keys = ['float32', 'float64', 'complex', 'complex_matrix']
        types = [np.float32, np.float64, np.complex128, np.ndarray]
        self.helper(self.data.num, keys, types)
        self.assertEqual(self.data.num.complex_matrix.dtype,
                         np.dtype('complex128'))

    def test_misc_num(self):
        ''' Test incoming misc numeric types '''
        keys = ['inf', 'NaN', 'matrix', 'vector', 'column_vector', 'matrix3d']
        types = [np.float64, np.float64, np.ndarray, np.ndarray, np.ndarray,
                 np.ndarray]
        self.helper(self.data.num, keys, types)

    def test_logical(self):
        ''' Test incoming logical type '''
        self.assertEqual(type(self.data.logical), np.ndarray)

    def test_string(self):
        ''' Test incoming string types '''
        keys = ['basic', 'char_array', 'cell_array']
        types = [str, list, list]
        self.helper(self.data.string, keys, types)

    def test_struct(self):
        ''' Test incoming struct types '''
        keys = ['name', 'age']
        types = [list, list]
        self.helper(self.data.struct.array, keys, types)

    def test_cell_array(self):
        ''' Test incoming cell array types '''
        keys = ['vector', 'matrix']
        types = [list, list]
        self.helper(self.data.cell, keys, types)


if __name__ == '__main__':
    print 'py2oct test'
    print '*' * 20
    unittest.main()

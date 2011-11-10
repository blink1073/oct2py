import unittest
from py2oct import Octave
import numpy as np

class OctaveRoundtripTest(unittest.TestCase):

    def setUp(self):
        ''' Open an instance of Octave and get a struct with all of the datatypes
        '''
        self.oc = Octave()
        self.data = self.oc.test_datatypes()

    def helper(self, outgoing):
        ''' Uses roundtrip.m to make sure the data goes out and comes back intact
        '''
        incoming = self.oc.roundtrip(outgoing)
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
        for key in ['int8', 'int16', 'int32', 'int64',
                    'uint8', 'uint16', 'uint32', 'uint64']:
            self.helper(self.data.num.int[key])

    def test_float(self):
        for key in ['float32', 'float64', 'complex', 'complex_matrix']:
            self.helper(self.data.num[key])

    def test_misc_num(self):
        for key in ['inf', 'NaN', 'matrix', 'vector', 'column_vector', 'matrix3d']:
            self.helper(self.data.num[key])

    def test_logical(self):
        self.helper(self.data.logical)

    def test_string(self):
        # XXX cell_array is not implmentend
        for key in ['basic', 'cell_array']:
            self.helper(self.data.string[key])

    def test_struct(self):
        for key in ['name', 'age']:
            self.helper(self.data.struct.array[key])

    def test_cell_array(self):
        # XXX Not implemented
        return
        for key in ['vector', 'matrix']:
            self.helper(self.data.cell[key])

class OctaveIncomingTest(unittest.TestCase):

    def setUp(self):
        ''' Open an instance of Octave and get a struct with all of the datatypes
        '''
        self.oc = Octave()
        self.data = self.oc.test_datatypes()

    def helper(self, base, keys, types):
        for key, type_ in zip(keys, types):
            self.assertEqual(type(base[key]), type_)

    def test_int(self):
        keys = ['int8', 'int16', 'int32', 'int64',
                    'uint8', 'uint16', 'uint32', 'uint64']
        types = [np.int8, np.int16, np.int32, np.int64,
                    np.uint8, np.uint16, np.uint32, np.uint64]
        self.helper(self.data.num.int, keys, types)

    def test_floats(self):
        keys = ['float32', 'float64', 'complex', 'complex_matrix']
        types = [np.float32, np.float64, np.complex128, np.ndarray]
        self.helper(self.data.num, keys, types)
        self.assertEqual(self.data.num.complex_matrix.dtype, np.dtype('complex128'))

    def test_misc_num(self):
        keys = ['inf', 'NaN', 'matrix', 'vector', 'column_vector', 'matrix3d']
        types = [np.float64, np.float64, np.ndarray, np.ndarray, np.ndarray, np.ndarray]
        self.helper(self.data.num, keys, types)

    def test_logical(self):
        self.assertEqual(type(self.data.logical), np.ndarray)

    def test_string(self):
        keys = ['basic', 'char_array', 'cell_array']
        types = [str, list, list]
        self.helper(self.data.string, keys, types)

    def test_struct(self):
        keys = ['name', 'age']
        types = [list, list]
        self.helper(self.data.struct.array, keys, types)

    def test_cell_array(self):
        keys = ['vector', 'matrix']
        types = [list, list]
        self.helper(self.data.cell, keys, types)


if __name__ == '__main__':
    print 'py2oct test'
    print '*' * 20
    unittest.main()

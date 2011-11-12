''' py2oct_test - Test value passing between python and octave
'''
import unittest
import numpy as np
from oct2py import octave

class RoundtripTest(): #unittest.TestCase):
    ''' Test roundtrip value and type preservation between Python and Octave

    Uses test_datatypes.m to read in a dictionary with all Octave types
    uses roundtrip.m to send each of the values out and back,
        making sure the value and the type are preserved.
    '''
    def setUp(self):
        ''' Open an instance of Octave and get a struct with all
             of the datatypes
        '''
        self.data = octave.test_datatypes()

    def helper(self, outgoing):
        ''' Uses roundtrip.m to make sure the data goes out
            and comes back intact
        '''
        incoming = octave.roundtrip(outgoing)
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
            # floats are converted to doubles by Octave
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
                    'matrix3d', 'matrix5d']:
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


class IncomingTest(): #unittest.TestCase):
    ''' Test the importing of all Octave data types, checking their type

    Uses test_datatypes.m to read in a dictionary with all Octave types
    Tests the types of all the values to make sure they were
        brought in properly.
    '''
    def setUp(self):
        ''' Open an instance of Octave and get a struct with all of the
            datatypes
        '''
        self.data = octave.test_datatypes()

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
        keys = ['inf', 'NaN', 'matrix', 'vector', 'column_vector', 'matrix3d',
                'matrix5d']
        types = [np.float64, np.float64, np.ndarray, np.ndarray, np.ndarray,
                 np.ndarray, np.ndarray]
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
        
        
class BuiltinsTest(unittest.TestCase):
    ''' Test the exporting of standard Python data types, checking their type

    Runs roundtrip.m and tests the types of all the values to make sure they
    were brought in properly.
    '''
    def helper(self, outgoing, incoming=None):
        ''' Uses roundtrip.m to make sure the data goes out
            and comes back intact
        '''
        if incoming is None:
            incoming = octave.roundtrip(outgoing)
        try:
            self.assertEqual(incoming, outgoing)
            self.assertEqual(type(incoming), type(outgoing))
        except ValueError:
            # np arrays must be compared specially
            assert np.allclose(incoming, outgoing)
        
    def test_dict(self):
        ''' Test python dictionary '''
        test = dict(x='spam', y=[1,2,3])
        incoming = octave.roundtrip(test)
        incoming = dict(incoming)
        for key in incoming:
            self.helper(test[key], incoming[key])
        
    def test_set(self):
        ''' Test python set '''
        test = (1, 2, 3, 3)
        self.helper(test)
        
    def test_list(self):
        tests = [[1, 2], ['a', 'b']]
        for test in tests:
            self.helper(test)
            
    def test_int(self):
        test = np.random.randint(1000)
        incoming = octave.roundtrip(test)
        self.assertEqual(incoming, test)
        self.assertEqual(type(incoming), np.int32)
            
    def test_float(self):
        test = np.pi
        incoming = octave.roundtrip(test)
        self.assertEqual(incoming, test)
        self.assertEqual(type(incoming), np.float64)
        
    def test_string(self):
        tests = ['spam', u'eggs']
        self.helper(tests[0])
        incoming = octave.roundtrip(tests[1])
        self.assertEqual(incoming, tests[1])
        self.assertEqual(type(incoming), str)
        
    def test_nested_list(self):
        #test = [['spam', 'eggs'], ['foo ', 'bar ']]
        #XXX need to implement nested strings
        test = [[1, 2], [3, 4]]
        self.helper(test)
        
class NumpyTest(unittest.TestCase):
    
    def setUp(self):
        self.codes = []
        for typecode in np.typecodes['All']:
            # XXX implement these other types
            if typecode not in  ['?', 'e', 'g', 'F', 'G', 'S', 'U', 'V', 'O', 
                                 'M', 'm']: 
                self.codes.append(typecode)
                
    def test_scalars(self):
        for typecode in self.codes:
            outgoing = (np.random.randint(-255, 255) + np.random.rand(1))
            outgoing = outgoing.astype(typecode)
            incoming = octave.roundtrip(outgoing)
            self.assertEqual(outgoing, incoming)
    
    def test_ndarrays(self):
        for typecode in self.codes:
            ndims = np.random.randint(1, 4)
            size = [np.random.randint(1, 10) for i in range(ndims)]
            outgoing = (np.random.randint(-255, 255, tuple(size)))
            outgoing += np.random.rand(*size)
            outgoing = outgoing.astype(typecode)
            incoming = octave.roundtrip(outgoing)
            assert np.allclose(incoming, outgoing)

    
if __name__ == '__main__':
    print 'py2oct test'
    print '*' * 20
    unittest.main()

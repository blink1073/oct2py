"""
oct2py_test - Test value passing between python and Octave.

Known limitations
-----------------
* The following Numpy array types cannot be sent directly via a MAT file.  The
float16/96/128 and complex192/256 can be recast as float64 and complex128.
   ** float16('e')
   ** float96('g')
   ** float128
   ** complex192('G')
   ** complex256
   ** read-write buffer('V')
"""
from __future__ import absolute_import, print_function
import logging
import os
import numpy as np
import numpy.testing as test
import oct2py
from oct2py import Oct2Py, Oct2PyError
from oct2py.utils import Struct
from oct2py.compat import unicode, long, PY2


octave = Oct2Py()
octave.addpath(os.path.dirname(__file__))
DATA = octave.test_datatypes()


TYPE_CONVERSIONS = [(int, 'int32', np.int32),
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
                (np.complex128, 'double', np.complex128), ]


class TypeConversions(test.TestCase):
    """Test roundtrip datatypes starting from Python
    """

    def test_python_conversions(self):
        """Test roundtrip python type conversions
        """
        for out_type, oct_type, in_type in TYPE_CONVERSIONS:
            if out_type == dict:
                outgoing = dict(x=1)
            elif out_type == None:
                outgoing = None
            else:
                outgoing = out_type(1)
            incoming, octave_type = octave.roundtrip(outgoing)
            if octave_type == 'int32' and oct_type == 'int64':
                pass
            elif octave_type == 'char' and oct_type == 'cell':
                pass
            elif octave_type == 'single' and oct_type == 'double':
                pass
            elif octave_type == 'int64' and oct_type == 'int32':
                pass
            else:
                self.assertEqual(octave_type, oct_type)
            if type(incoming) != in_type:
                if type(incoming) == np.int32 and in_type == np.int64:
                    pass
                else:
                    assert in_type(incoming) == incoming


class IncomingTest(test.TestCase):
    """Test the importing of all Octave data types, checking their type

    Uses test_datatypes.m to read in a dictionary with all Octave types
    Tests the types of all the values to make sure they were
        brought in properly.

    """
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
        self.helper(DATA.num.int, keys, types)

    def test_floats(self):
        """Test incoming float types
        """
        keys = ['float32', 'float64', 'complex', 'complex_matrix']
        types = [np.float64, np.float64, np.complex128, np.ndarray]
        self.helper(DATA.num, keys, types)
        self.assertEqual(DATA.num.complex_matrix.dtype,
                         np.dtype('complex128'))

    def test_misc_num(self):
        """Test incoming misc numeric types
        """
        keys = ['inf', 'NaN', 'matrix', 'vector', 'column_vector', 'matrix3d',
                'matrix5d']
        types = [np.float64, np.float64, np.ndarray, np.ndarray, np.ndarray,
                 np.ndarray, np.ndarray]
        self.helper(DATA.num, keys, types)

    def test_logical(self):
        """Test incoming logical type
        """
        self.assertEqual(type(DATA.logical), np.ndarray)

    def test_string(self):
        """Test incoming string types
        """
        keys = ['basic', 'char_array', 'cell_array']
        types = [unicode, list, list]
        self.helper(DATA.string, keys, types)

    def test_struct_array(self):
        ''' Test incoming struct array types '''
        keys = ['name', 'age']
        types = [list, list]
        self.helper(DATA.struct_array, keys, types)

    def test_cell_array(self):
        ''' Test incoming cell array types '''
        keys = ['vector', 'matrix']
        types = [list, list]
        self.helper(DATA.cell, keys, types)

    def test_mixed_struct(self):
        '''Test mixed struct type
        '''
        keys = ['array', 'cell', 'scalar']
        types = [list, list, float]
        self.helper(DATA.mixed, keys, types)


class RoundtripTest(test.TestCase):
    """Test roundtrip value and type preservation between Python and Octave.

    Uses test_datatypes.m to read in a dictionary with all Octave types
    uses roundtrip.m to send each of the values out and back,
        making sure the value and the type are preserved.

    """
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
        incoming = octave.roundtrip(outgoing)
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
            self.helper(DATA.num.int[key])

    def test_float(self):
        """Test roundtrip value and type preservation for float types
        """
        for key in ['float64', 'complex', 'complex_matrix']:
            self.helper(DATA.num[key])
        self.helper(DATA.num['float32'], np.float64)

    def test_misc_num(self):
        """Test roundtrip value and type preservation for misc numeric types
        """
        for key in ['inf', 'NaN', 'matrix', 'vector', 'column_vector',
                    'matrix3d', 'matrix5d']:
            self.helper(DATA.num[key])

    def test_logical(self):
        """Test roundtrip value and type preservation for logical type
        """
        self.helper(DATA.logical)

    def test_string(self):
        """Test roundtrip value and type preservation for string types
        """
        for key in ['basic', 'cell_array']:
            self.helper(DATA.string[key])

    def test_struct_array(self):
        """Test roundtrip value and type preservation for struct array types
        """
        self.helper(DATA.struct_array['name'])
        self.helper(DATA.struct_array['age'], np.ndarray)

    def test_cell_array(self):
        """Test roundtrip value and type preservation for cell array types
        """
        for key in ['vector', 'matrix', 'array']:
            self.helper(DATA.cell[key])
        #self.helper(DATA.cell['array'], np.ndarray)

    def test_octave_origin(self):
        '''Test all of the types, originating in octave, and returning
        '''
        octave.run('x = test_datatypes()')
        octave.put('y', DATA)
        for key in DATA.keys():
            if key != 'struct_array':
                cmd = 'isequalwithequalnans(x.{0},y.{0})'.format(key)
                ret = octave.run(cmd)
                assert ret == 'ans =  1'


class BuiltinsTest(test.TestCase):
    """Test the exporting of standard Python data types, checking their type.

    Runs roundtrip.m and tests the types of all the values to make sure they
    were brought in properly.

    """
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
            incoming = octave.roundtrip(outgoing)
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
            incoming = octave.roundtrip(outgoing)
            assert expected_type(incoming) == incoming

    def test_dict(self):
        """Test python dictionary
        """
        test = dict(x='spam', y=[1, 2, 3])
        incoming = octave.roundtrip(test)
        #incoming = dict(incoming)
        for key in incoming:
            self.helper(test[key], incoming[key])

    def test_nested_dict(self):
        """Test nested python dictionary
        """
        test = dict(x=dict(y=1e3, z=[1, 2]), y='spam')
        incoming = octave.roundtrip(test)
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
        incoming = octave.roundtrip(test)
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
        for test in tests:
            self.helper(test)

    def test_nested_list(self):
        """Test python nested lists
        """
        test = [['spam', 'eggs'], ['foo ', 'bar ']]
        self.helper(test, expected_type=list)
        test = [[1, 2], [3, 4]]
        self.helper(test)
        test = [[1, 2], [3, 4, 5]]
        incoming = octave.roundtrip(test)
        for i in range(len(test)):
            assert np.alltrue(incoming[i] == np.array(test[i]))

    def test_bool(self):
        """Test boolean values
        """
        tests = (True, False)
        for test in tests:
            incoming = octave.roundtrip(test)
            self.assertEqual(incoming, test)
            self.assertEqual(incoming.dtype, np.dtype('int8'))

    def test_none(self):
        """Test sending None type
        """
        incoming = octave.roundtrip(None)
        assert np.isnan(incoming)


class NumpyTest(test.TestCase):
    """Check value and type preservation of Numpy arrays
    """
    codes = np.typecodes['All']
    blacklist_codes = 'V'
    blacklist_names = ['float128', 'float96', 'complex192', 'complex256']

    def test_scalars(self):
        """Send a scalar numpy type and make sure we get the same number back.
        """
        for typecode in self.codes:
            outgoing = (np.random.randint(-255, 255) + np.random.rand(1))
            try:
                outgoing = outgoing.astype(typecode)
            except TypeError:
                continue
            if (typecode in self.blacklist_codes or
                outgoing.dtype.name in self.blacklist_names):
                self.assertRaises(Oct2PyError, octave.roundtrip, outgoing)
                continue
            incoming = octave.roundtrip(outgoing)
            if outgoing.dtype.str in ['<M8[us]', '<m8[us]']:
                outgoing = outgoing.astype(np.uint64)
            try:
                assert np.allclose(incoming, outgoing)
            except (ValueError, TypeError, NotImplementedError,
                     AssertionError):
                assert np.alltrue(np.array(incoming).astype(typecode) ==
                                   outgoing)

    def test_ndarrays(self):
        """Send an ndarray and make sure we get the same array back
        """
        for typecode in self.codes:
            for ndims in [2, 3, 4]:
                size = [np.random.randint(1, 10) for i in range(ndims)]
                outgoing = (np.random.randint(-255, 255, tuple(size)))
                outgoing += np.random.rand(*size)
                if typecode in ['U', 'S']:
                    outgoing = [[['spam', 'eggs'], ['spam', 'eggs']],
                                [['spam', 'eggs'], ['spam', 'eggs']]]
                    outgoing = np.array(outgoing).astype(typecode)
                else:
                    try:
                        outgoing = outgoing.astype(typecode)
                    except TypeError:
                        continue
                if (typecode in self.blacklist_codes or
                     outgoing.dtype.name in self.blacklist_names):
                    self.assertRaises(Oct2PyError, octave.roundtrip, outgoing)
                    continue
                incoming = octave.roundtrip(outgoing)
                incoming = np.array(incoming)
                if outgoing.size == 1:
                    outgoing = outgoing.squeeze()
                if len(outgoing.shape) > 2 and 1 in outgoing.shape:
                    incoming = incoming.squeeze()
                    outgoing = outgoing.squeeze()
                elif incoming.size == 1:
                    incoming = incoming.squeeze()
                assert incoming.shape == outgoing.shape
                if outgoing.dtype.str in ['<M8[us]', '<m8[us]']:
                    outgoing = outgoing.astype(np.uint64)
                try:
                    assert np.allclose(incoming, outgoing)
                except (AssertionError, ValueError, TypeError,
                         NotImplementedError):
                    if 'c' in incoming.dtype.str:
                        incoming = np.abs(incoming)
                        outgoing = np.abs(outgoing)
                    assert np.alltrue(np.array(incoming).astype(typecode) ==
                                       outgoing)

    def test_sparse(self):
        '''Test roundtrip sparse matrices
        '''
        from scipy.sparse import csr_matrix, identity
        rand = np.random.rand(100, 100)
        rand = csr_matrix(rand)
        iden = identity(1000)
        for test in [rand, iden]:
            incoming, type_ = octave.roundtrip(test)
            assert test.shape == incoming.shape
            assert test.nnz == incoming.nnz
            assert np.allclose(test.todense(), incoming.todense())
            assert test.dtype == incoming.dtype
            assert (type_ == 'double' or type_ == 'cell')

    def test_empty(self):
        '''Test roundtrip empty matrices
        '''
        test = np.empty((100, 100))
        incoming, type_ = octave.roundtrip(test)
        assert test.squeeze().shape == incoming.squeeze().shape
        assert np.allclose(test[np.isfinite(test)],
                            incoming[np.isfinite(incoming)])
        assert type_ == 'double'

    def test_mat(self):
        '''Verify support for matrix type
        '''
        test = np.random.rand(1000)
        test = np.mat(test)
        incoming, type_ = octave.roundtrip(test)
        assert np.allclose(test, incoming)
        assert test.dtype == incoming.dtype
        assert type_ == 'double'

    def test_masked(self):
        '''Test support for masked arrays
        '''
        test = np.random.rand(100)
        test = np.ma.array(test)
        incoming, type_ = octave.roundtrip(test)
        assert np.allclose(test, incoming)
        assert test.dtype == incoming.dtype
        assert type_ == 'double'


class BasicUsageTest(test.TestCase):
    """Excercise the basic interface of the package
    """
    def test_run(self):
        """Test the run command
        """
        out = octave.run('y=ones(3,3)')
        desired = """y =

        1        1        1
        1        1        1
        1        1        1
"""
        self.assertEqual(out, desired)
        out = octave.run('x = mean([[1, 2], [3, 4]])', verbose=True)
        self.assertEqual(out, 'x =  2.5000')
        self.assertRaises(Oct2PyError, octave.run, '_spam')

    def test_call(self):
        """Test the call command
        """
        out = octave.call('ones', 1, 2)
        assert np.allclose(out, np.ones((1, 2)))
        U, S, V = octave.call('svd', [[1, 2], [1, 3]])
        assert np.allclose(U, ([[-0.57604844, -0.81741556],
                            [-0.81741556, 0.57604844]]))
        assert np.allclose(S,  ([[3.86432845, 0.],
                             [0., 0.25877718]]))
        assert np.allclose(V,  ([[-0.36059668, -0.93272184],
         [-0.93272184, 0.36059668]]))
        out = octave.call('roundtrip.m', 1)
        self.assertEqual(out, 1)
        fname = os.path.join(__file__, 'roundtrip.m')
        out = octave.call(fname, 1)
        self.assertEqual(out, 1)
        self.assertRaises(Oct2PyError, octave.call, '_spam')

    def test_put_get(self):
        """Test putting and getting values
        """
        octave.put('spam', [1, 2])
        out = octave.get('spam')
        assert np.allclose(out, np.array([1, 2]))
        octave.put(['spam', 'eggs'], ['foo', [1, 2, 3, 4]])
        spam, eggs = octave.get(['spam', 'eggs'])
        self.assertEqual(spam, 'foo')
        assert np.allclose(eggs, np.array([[1, 2, 3, 4]]))
        self.assertRaises(Oct2PyError, octave.put, '_spam', 1)
        self.assertRaises(Oct2PyError, octave.get, '_spam')

    def test_help(self):
        """Testing help command
        """
        out = octave.cos.__doc__
        try:
            self.assertEqual(out[:5], '\ncos ')
        except AssertionError:
            self.assertEqual(out[:5], '\n`cos')

    def test_dynamic(self):
        """Test the creation of a dynamic function
        """
        tests = [octave.zeros, octave.ones, octave.plot]
        for test in tests:
            try:
                self.assertEqual(repr(type(test)), "<type 'function'>")
            except AssertionError:
                self.assertEqual(repr(type(test)), "<class 'function'>")
        self.assertRaises(Oct2PyError, octave.__getattr__, 'aaldkfasd')
        self.assertRaises(Oct2PyError, octave.__getattr__, '_foo')
        self.assertRaises(Oct2PyError, octave.__getattr__, 'foo\W')

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

    def test_syntax_error(self):
        """Make sure a syntax error in Octave throws an Oct2PyError
        """
        oc = Oct2Py()
        self.assertRaises(Oct2PyError, oc._eval, "a='1")
        oc = Oct2Py()
        self.assertRaises(Oct2PyError, oc._eval, "a=1++3")

def test_unicode_docstring():
    '''Make sure unicode docstrings in Octave functions work'''
    help(octave.test_datatypes)


def test_context_manager():
    '''Make sure oct2py works within a context manager'''
    oc = Oct2Py()
    with oc as oc1:
        ones = oc1.ones(1)
    assert ones == np.ones(1)
    with oc as oc2:
         ones = oc2.ones(1)
    assert ones == np.ones(1)


def test_singleton_sparses():
    '''Make sure a singleton sparse matrix works'''
    import scipy.sparse
    data = scipy.sparse.csc.csc_matrix(1)
    oc = Oct2Py()
    oc.put('x', data)
    assert np.allclose(data.toarray(), oc.get('x').toarray())
    oc.put('y', [data])
    assert np.allclose(data.toarray(), oc.get('y').toarray())


def test_logging():
    # create a stringio and a handler to log to it
    def get_handler():
        if PY2:
            from StringIO import StringIO
        else:
            from io import StringIO
        sobj = StringIO()
        hdlr = logging.StreamHandler(sobj)
        hdlr.setLevel(logging.DEBUG)
        return hdlr

    oc = Oct2Py()
    hdlr = get_handler()
    oc.logger.addHandler(hdlr)

    # generate some messages (logged and not logged)
    oc.ones(1, verbose=True)

    oc.logger.setLevel(logging.DEBUG)
    oc.zeros(1)

    # check the output
    lines = hdlr.stream.getvalue().strip().split('\n')
    assert len(lines) == 21
    assert lines[0].startswith('load')

    # now make an object with a desired logger
    logger = oct2py.get_log('test')
    hdlr = get_handler()
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)
    oc2 = Oct2Py(logger=logger)

     # generate some messages (logged and not logged)
    oc2.ones(1, verbose=True)

    oc2.logger.setLevel(logging.DEBUG)
    oc2.zeros(1)

    # check the output
    lines = hdlr.stream.getvalue().strip().split('\n')
    assert len(lines) == 39
    assert lines[0].startswith('load')


def test_demo():
    from oct2py import demo
    try:
        demo.demo(0.01, interactive=False)
    except AttributeError:
        demo(0.01, interactive=False)


def test_lookfor():
    assert 'cosd' in octave.lookfor('cos')


def test_remove_files():
    from oct2py.utils import _remove_temp_files
    _remove_temp_files()


def test_speed():
    from oct2py import speed_test
    speed_test()


def test_threads():
    from oct2py import thread_test
    thread_test()


def test_plot():
    octave.plot([1])
    

def test_narg_out():
    oc = Oct2Py()
    s = oc.svd(np.array([[1,2], [1,3]]))
    assert s.shape == (2, 1)
    U, S, V = oc.svd([[1,2], [1,3]])
    assert U.shape == S.shape == V.shape == (2, 2)


def test_help():
    help(Oct2Py())


def test_trailing_underscore():
    oc = Oct2Py()
    x = oc.ones_()
    assert np.allclose(x, np.ones(1))


def test_using_closed_session():
    oc = Oct2Py()
    oc.close()
    test.assert_raises(Oct2PyError, oc.call, 'ones')

    
if __name__ == '__main__':  # pragma: no cover
    print('oct2py test')
    print('*' * 20)
    test.run_module_suite()

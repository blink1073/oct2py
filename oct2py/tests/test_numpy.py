from __future__ import absolute_import, print_function
import os

import numpy as np

from oct2py import Oct2Py


class TestNumpy:
    """Check value and type preservation of Numpy arrays
    """
    codes = np.typecodes['All']

    @classmethod
    def setup_class(cls):
        cls.oc = Oct2Py()
        cls.oc.addpath(os.path.dirname(__file__))

    def teardown_class(cls):
        cls.oc.exit()

    def test_scalars(self):
        """Send scalar numpy types and make sure we get the same number back.
        """
        for typecode in self.codes:
            if typecode == 'V':
                continue
            outgoing = (np.random.randint(-255, 255) + np.random.rand(1))
            if typecode in 'US':
                outgoing = np.array('spam').astype(typecode)
            try:
                outgoing = outgoing.astype(typecode)
            except TypeError:
                continue
            incoming = self.oc.roundtrip(outgoing)
            try:
                assert np.allclose(incoming, outgoing)
            except (ValueError, TypeError, NotImplementedError,
                    AssertionError):
                assert np.alltrue(np.array(incoming).astype(typecode) ==
                                  outgoing)

    def test_ndarrays(self):
        """Send ndarrays and make sure we get the same array back
        """
        for typecode in self.codes:
            if typecode == 'V':
                continue
            for ndims in [2, 3, 4]:
                size = [np.random.randint(1, 10) for i in range(ndims)]
                outgoing = (np.random.randint(-255, 255, tuple(size)))
                try:
                    outgoing += np.random.rand(*size).astype(outgoing.dtype,
                                                             casting='unsafe')
                except TypeError:  # pragma: no cover
                    outgoing += np.random.rand(*size).astype(outgoing.dtype)
                if typecode in ['U', 'S']:
                    outgoing = [[['spam', 'eggs', 'hash'],
                                 ['spam', 'eggs', 'hash']],
                                [['spam', 'eggs', 'hash'],
                                 ['spam', 'eggs', 'hash']]]
                    outgoing = np.array(outgoing).astype(typecode)
                else:
                    try:
                        outgoing = outgoing.astype(typecode)
                    except TypeError:
                        continue
                incoming = self.oc.roundtrip(outgoing)
                incoming = np.array(incoming)
                if outgoing.size == 1:
                    outgoing = outgoing.squeeze()
                if len(outgoing.shape) > 2 and 1 in outgoing.shape:
                    incoming = incoming.squeeze()
                    outgoing = outgoing.squeeze()
                elif incoming.size == 1:
                    incoming = incoming.squeeze()
                if typecode == 'O':
                    incoming = incoming.squeeze()
                    outgoing = outgoing.squeeze()
                assert incoming.shape == outgoing.shape
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
        for item in [rand, iden]:
            incoming, type_ = self.oc.roundtrip(item, nout=2)
            assert item.shape == incoming.shape
            assert item.nnz == incoming.nnz
            assert np.allclose(item.todense(), incoming.todense())
            assert item.dtype == incoming.dtype
            assert (type_ == 'double' or type_ == 'cell')

    def test_empty(self):
        '''Test roundtrip empty matrices
        '''
        empty = np.empty((100, 100))
        incoming, type_ = self.oc.roundtrip(empty, nout=2)
        assert empty.squeeze().shape == incoming.squeeze().shape
        assert np.allclose(empty[np.isfinite(empty)],
                           incoming[np.isfinite(incoming)])
        assert type_ == 'double'

    def test_mat(self):
        '''Verify support for matrix type
        '''
        test = np.random.rand(1000)
        test = np.mat(test)
        incoming, type_ = self.oc.roundtrip(test, nout=2)
        assert np.allclose(test, incoming)
        assert test.dtype == incoming.dtype
        assert type_ == 'double'

    def test_masked(self):
        '''Test support for masked arrays
        '''
        test = np.random.rand(100)
        test = np.ma.array(test)
        incoming, type_ = self.oc.roundtrip(test, nout=2)
        assert np.allclose(test, incoming)
        assert test.dtype == incoming.dtype
        assert type_ == 'double'

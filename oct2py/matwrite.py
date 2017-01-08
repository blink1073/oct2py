"""
.. module:: _h5write
   :synopsis: Write Python values into an MAT file for Octave.
              Strives to preserve both value and type in transit.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import absolute_import, print_function, division

from scipy.io import savemat
from scipy.sparse import csr_matrix, csc_matrix
import numpy as np

from .utils import Oct2PyError


class Writer(object):
    """An object used to write Python objects to a MAT file.
    """

    def write_file(self, obj, path, oned_as='row', convert_to_float=True):
        """Save a Python object to an Octave file on the given path.
        """
        self.convert_to_float = convert_to_float
        data = self._encode(obj)
        try:
            savemat(path, data, appendmat=False, oned_as=oned_as,
                    long_field_names=True)
        except KeyError:  # pragma: no cover
            raise Exception('could not save mat file')

    def _encode(self, data):
        """Convert the Python values to values suitable to sent to Octave.
        """

        # Extract the values from dict and Struct objects.
        if isinstance(data, dict):
            for (key, value) in data.items():
                data[key] = self._encode(value)

        # Send None as nan.
        if data is None:
            return np.NaN

        # See if it should be an array, otherwise treat is as a tuple.
        if isinstance(data, list):
            try:
                test = np.array(data)
                if test.dtype.kind in 'uicf':
                    return self._encode(test)
            except Exception:
                pass
            return self._encode(tuple(data))

        # Make a cell or a cell array.
        if isinstance(data, (tuple, set)):
            data = [self._encode(o) for o in data]
            # Use a trick to force a cell.
            if len(data) == 1:
                cell = np.zeros((1,), dtype=np.object)
                cell[0] = data
                return cell
            # Cell array.
            return np.array(data, dtype=object)

        # Convert sparse matrices to ndarrays.
        if isinstance(data, (csr_matrix, csc_matrix)):
            return data.astype(np.float64)

        # Clean up nd arrays.
        if isinstance(data, np.ndarray):
            return self._clean_array(data)

        # Leave all other content alone.
        return data

    def _clean_array(self, data):
        """Handle data type considerations."""
        dstr = data.dtype.str
        if 'c' in dstr and dstr[-2:] == '24':
            raise Oct2PyError('Datatype not supported: {0}'.format(data.dtype))
        elif 'f' in dstr and dstr[-2:] == '12':
            raise Oct2PyError('Datatype not supported: {0}'.format(data.dtype))
        elif 'V' in dstr and not hasattr(data, 'classname'):
            raise Oct2PyError('Datatype not supported: {0}'.format(data.dtype))
        elif dstr == '|b1':
            data = data.astype(np.int8)
        elif dstr == '<m8[us]' or dstr == '<M8[us]':
            data = data.astype(np.uint64)
        elif '|S' in dstr or '<U' in dstr:
            data = data.astype(np.object)
        elif '<c' in dstr and np.alltrue(data.imag == 0):
            data.imag = 1e-9
        if data.dtype.name in ['float128', 'complex256']:
            raise Oct2PyError('Datatype not supported: {0}'.format(data.dtype))
        if self.convert_to_float and data.dtype.kind in 'uib':
            data = data.astype(float)

        return data

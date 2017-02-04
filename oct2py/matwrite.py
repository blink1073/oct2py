"""
.. module:: matwrite
   :synopsis: Write Python values into an MAT file for Octave.
              Strives to preserve both value and type in transit.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import absolute_import, print_function, division

from scipy.io import savemat
from scipy.sparse import spmatrix
import numpy as np

from .dynamic import OctaveVariablePtr, OctaveUserClass


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

        # Extract the data from a variable pointer.
        if isinstance(data, OctaveVariablePtr):
            data = data.value

        # Extract the data from a user defined object.
        elif isinstance(data, OctaveUserClass):
            data = OctaveUserClass.to_value(data)

        # Extract the values from dict and Struct objects.
        if isinstance(data, dict):
            out = dict()
            for (key, value) in data.items():
                out[key] = self._encode(value)
            return out

        # Send None as nan.
        if data is None:
            return np.NaN

        # Handle list-like types.
        if isinstance(data, (tuple, set, list)):
            is_tuple = isinstance(data, tuple)
            data = [self._encode(o) for o in data]

            if not is_tuple:
                # Convert to a numeric array if possible.
                try:
                    return self._handle_list(data)
                except ValueError:
                    pass

            # Create a cell object.
            cell = np.empty((len(data),), dtype=object)
            for i in range(len(data)):
                cell[i] = data[i]
            return cell

        # Sparse data must be floating type.
        if isinstance(data, spmatrix):
            return data.astype(np.float64)

        # Return other data types unchanged.
        if not isinstance(data, np.ndarray):
            return data

        # Convert string types to objects so the length is read properly.
        if data.dtype.kind in 'US':
            return data.astype(object)

        # Complex 128 is the highest supported by savemat.
        if data.dtype.name == 'complex256':
            return data.astype(np.complex128)

        # Convert to float if applicable.
        if self.convert_to_float and data.dtype.kind in 'ui':
            return data.astype(np.float64)

        return data

    def _handle_list(self, data):
        """Handle an encoded list."""

        # Convert to an array.
        data = np.array(data)

        # Only handle numeric types.
        if data.dtype.kind not in 'uicf':
            raise ValueError

        # Handle any other ndarray considerations.
        return self._encode(data)

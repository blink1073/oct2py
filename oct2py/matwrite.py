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
from .utils import StructArray, StructElement


def write_file(obj, path, oned_as='row', convert_to_float=True):
    """Save a Python object to an Octave file on the given path.
    """
    data = _encode(obj, convert_to_float)
    try:
        savemat(path, data, appendmat=False, oned_as=oned_as,
                long_field_names=True)
    except KeyError:  # pragma: no cover
        raise Exception('could not save mat file')


def _encode(data, convert_to_float):
    """Convert the Python values to values suitable to sent to Octave.
    """

    # Handle variable pointer.
    if isinstance(data, (OctaveVariablePtr)):
        data = data.value

    # Handle a user defined object.
    elif isinstance(data, OctaveUserClass):
        data = OctaveUserClass.to_value(data)

    # Handle struct array.
    elif isinstance(data, StructArray):
        data = StructArray.to_value(data)

    # Handle struct element.
    elif isinstance(data, StructElement):
        data = StructElement.to_value(data)

    # Extract the values from dict and Struct objects.
    if isinstance(data, dict):
        out = dict()
        for (key, value) in data.items():
            out[key] = _encode(value, convert_to_float)
        return out

    # Send None as nan.
    if data is None:
        return np.NaN

    # Handle list-like types.
    if isinstance(data, (tuple, set, list)):
        is_tuple = isinstance(data, tuple)
        data = [_encode(o, convert_to_float) for o in data]

        if not is_tuple:
            # Convert to a numeric array if possible.
            try:
                return _handle_list(data, convert_to_float)
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

    # Complex 128 is the highest supported by savemat.
    if data.dtype.name == 'complex256':
        return data.astype(np.complex128)

    # Convert to float if applicable.
    if convert_to_float and data.dtype.kind in 'ui':
        return data.astype(np.float64)

    return data


def _handle_list(data, convert_to_float):
    """Handle an encoded list."""

    # Convert to an array.
    data = np.array(data)

    # Only handle numeric types.
    if data.dtype.kind not in 'uicf':
        raise ValueError

    # Handle any other ndarray considerations.
    return _encode(data, convert_to_float)

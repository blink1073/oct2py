"""
.. module:: _h5write
   :synopsis: Write Python values into an MAT file for Octave.
              Strives to preserve both value and type in transit.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import absolute_import, print_function, division

from scipy.io import savemat
import numpy as np
from scipy.sparse import csr_matrix, csc_matrix

from .utils import Oct2PyError
from .compat import unicode


def write_file(obj, path, oned_as='row', convert_to_float=True):
    """Save a Python object to an Octave file on the given path.
    """
    data = putvals(obj, convert_to_float=convert_to_float)
    try:
        savemat(path, dict(req=data), appendmat=False, oned_as=oned_as,
                long_field_names=True)
    except KeyError:  # pragma: no cover
        raise Exception('could not save mat file')


def putvals(dict_, convert_to_float=True):
    """
    Put a nested dict into the MAT file as a struct

    Parameters
    ==========
    dict_ : dict
        Dictionary of object(s) to store
    convert_to_float : bool
        If true, convert integer types to float

    Returns
    =======
    out : array
        Dictionary of object(s), ready for transit

    """
    data = dict()
    for key in dict_.keys():
        if isinstance(dict_[key], dict):
            data[key] = putvals(dict_[key], convert_to_float)
        else:
            data[key] = putval(dict_[key], convert_to_float)
    return data


def putval(data, convert_to_float=True):
    """
    Convert data into a state suitable for transfer.

    Parameters
    ==========
    data : object
        Value to write to file.
    convert_to_float : bool
        If true, convert integer types to float.

    Returns
    =======
    out : object
        Object, ready for transit

    Notes
    =====
    Several considerations must be made
    for data type to ensure proper read/write of the MAT file.
    Currently the following types supported: float96, complex192, void

    """
    if data is None:
        data = np.NaN
    if isinstance(data, set):
        data = list(data)
    if isinstance(data, (list, tuple)):
        # hack to get a viable cell object
        if str_in_list(data):
            try:
                data = np.array(data, dtype=np.object)
            except ValueError as err:  # pragma: no cover
                raise Oct2PyError(err)
        else:
            out = []
            for el in data:
                if isinstance(el, np.ndarray) or len(data) == 1:
                    cell = np.zeros((1,), dtype=np.object)
                    cell[0] = el
                    out.append(cell)
                elif isinstance(el, (csr_matrix, csc_matrix)):
                    out.append(el.astype(np.float64))
                else:
                    out.append(el)
            return out
    if isinstance(data, (str, unicode)):
        return data
    if isinstance(data, (csr_matrix, csc_matrix)):
        return data.astype(np.float64)
    try:
        data = np.array(data)
    except ValueError as err:  # pragma: no cover
        data = np.array(data, dtype=object)
    dstr = data.dtype.str
    if 'c' in dstr and dstr[-2:] == '24':
        raise Oct2PyError('Datatype not supported: {0}'.format(data.dtype))
    elif 'f' in dstr and dstr[-2:] == '12':
        raise Oct2PyError('Datatype not supported: {0}'.format(data.dtype))
    elif 'V' in dstr:
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
    if data.dtype == 'object' and len(data.shape) > 1:
        data = data.T
    if convert_to_float and data.dtype.kind in 'uib':
        data = data.astype(float)
    return data


def str_in_list(list_):
    '''See if there are any strings in the given list
    '''
    for item in list_:
        if isinstance(item, (str, unicode)):
            return True
        elif isinstance(item, (list, tuple)):
            if str_in_list(item):
                return True

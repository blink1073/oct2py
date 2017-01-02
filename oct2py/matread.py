"""
.. module:: matread
   :synopsis: Read Python values from a MAT file made by Octave.
              Strives to preserve both value and type in transit.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import absolute_import, print_function, division

import numpy as np
from scipy.io import loadmat
import scipy

from .dynamic import OctaveUserClass
from .utils import Struct, Oct2PyError


def read_file(path, session):
    """Read a file on the given path and return its data.
    """
    try:
        data = loadmat(path, struct_as_record=True)
    except UnicodeDecodeError as e:
        raise Oct2PyError(str(e))
    result = get_data(data['result'], session)
    return dict(result=result, error=data['err'])


def get_data(val, session):
    '''Extract the data from the incoming value
    '''
    # check for objects
    if val is None:
        return

    if isinstance(val, OctaveUserClass):
        return val

    if isinstance(val, np.ndarray) and hasattr(val, 'classname'):
        cls = session._get_user_class(val.classname)
        return cls.from_value(val)

    if "'|O" in str(val.dtype) or "O'" in str(val.dtype):
        data = Struct()
        for key in val.dtype.fields.keys():
            data[key] = get_data(val[key][0], session)
        return data

    # handle cell arrays
    if val.dtype == np.object:
        if val.size == 1:
            val = val[0]
            if "'|O" in str(val.dtype) or "O'" in str(val.dtype):
                val = get_data(val, session)
            if isinstance(val, Struct):
                return val
            if isinstance(val, OctaveUserClass):
                return val
            if val.size == 1:
                val = val.flatten()

    if val.dtype == np.object:
        if len(val.shape) > 2:
            val = val.T
            val = np.array([get_data(val[i].T, session)
                            for i in range(val.shape[0])])
        if len(val.shape) > 1:
            if len(val.shape) == 2:
                val = val.T
            try:
                return val.astype(val[0][0].dtype)
            except (ValueError, TypeError):
                # dig into the cell type
                for row in range(val.shape[0]):
                    for i in range(val[row].size):
                        if not np.isscalar(val[row][i]):
                            if val[row][i].size > 1:
                                val[row][i] = val[row][i].squeeze()
                            elif val[row][i].size:
                                val[row][i] = val[row][i][0]
                            else:
                                val[row][i] = val[row][i].tolist()
            except IndexError:
                return val.tolist()
        else:
            val = np.array([get_data(val[i], session)
                            for i in range(val.size)])
        if len(val.shape) == 1 or val.shape[0] == 1 or val.shape[1] == 1:
            val = val.flatten()
        val = val.tolist()
        if len(val) == 1 and isinstance(val[0],
                                        scipy.sparse.csc.csc_matrix):
            val = val[0]
    elif val.size == 1:
        if hasattr(val, 'flatten'):
            val = val.flatten()[0]
    elif val.size == 0:
        if val.dtype.kind in 'US':
            val = ''
        else:
            val = []

    return val

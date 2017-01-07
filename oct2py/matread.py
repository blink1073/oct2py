"""
.. module:: matread
   :synopsis: Read Python values from a MAT file made by Octave.
              Strives to preserve both value and type in transit.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import absolute_import, print_function, division

import numpy as np
from scipy.io import loadmat

from .utils import Struct, Oct2PyError


def read_file(path, session):
    """Read a file on the given path and return its data.
    """
    try:
        data = loadmat(path, struct_as_record=True)
    except UnicodeDecodeError as e:
        raise Oct2PyError(str(e))
    result = extract(data['result'], session)
    error = extract(data['err'], session)
    return result, error


def extract(val, session):
    """Parse the data from a MAT file into Pythonic objects.
    """

    # Parse each item of a list.
    if isinstance(val, list):
        return [extract(item, session) for item in val]

    # Return leaf objects unchanged.
    if not isinstance(val, np.ndarray):
        return val

    # Handle user defined classes.
    if hasattr(val, 'classname'):
        cls = session._get_user_class(val.classname)
        return cls.from_value(val)

    # Convert a record array to a Struct.
    if val.dtype.names:
        out = Struct()
        for name in val.dtype.names:
            out[name] = extract(val[name], session)
        return out

    # Handle opaque objects.
    if val.dtype.kind == 'O':
        val = extract(val.tolist(), session)
        # If it is a single cell, extract the inner value.
        if len(val) == 1 and isinstance(val[0], list):
            val = val[0]
        return val

    # Handle strings.
    if val.dtype.kind in 'US':
        val = extract(val.tolist(), session)
        # Extract the inner value of the string cell.
        if len(val) == 1:
            val = val[0]
        return val

    # Compress scalar types.
    if val.shape == (1, 1):
        val = np.asscalar(val)

    return val

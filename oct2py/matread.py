"""
.. module:: matread
   :synopsis: Read Python values from a MAT file made by Octave.
              Strives to preserve both value and type in transit.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import absolute_import, print_function, division

import numpy as np
from scipy.io import loadmat

from .compat import unicode
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
    """Parse the data from a MAT file into Pythonic objects.
    """

    # Parse each item of a list and collapse if it is redundantly nested.
    if isinstance(val, list):
        val = [get_data(v, session) for v in val]
        if len(val) == 1 and not isinstance(val[0], (str, unicode)):
            val = val[0]
        return val

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
            out[name] = get_data(val[name], session)
        return out

    # Handle opaque objects.
    if val.dtype == np.object:
        # These are transposed from their Python equivalents.
        if len(val.shape) > 1:
            val = val.T
        val = val.tolist()
        if isinstance(val, list):
            # Extract the cell objects.
            out = []
            for row in val:
                # Cell object.
                if len(row) == 1:
                    out.append(row[0])
                # Cell array object.
                else:
                    out.append(row)
            return get_data(out, session)

        return get_data(val, session)

    # Handle string arrays.
    if val.dtype.kind in 'US':
        # These are transposed from their Python equivalents.
        if len(val.shape) > 1:
            val = val.T
        val = get_data(val.tolist(), session)
        if len(val) == 1:
            val = val[0]
        return val

    # Compress scalar types.
    if val.shape == (1, 1):
        val = val.squeeze()

    return val

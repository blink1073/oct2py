"""
.. module:: matread
   :synopsis: Read Python values from a MAT file made by Octave.
              Strives to preserve both value and type in transit.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import absolute_import, print_function, division

import numpy as np
from scipy.io import loadmat

from .utils import Struct, StructArray, Oct2PyError


class Reader(object):
    """An object used to read objects from a MAT file.
    """

    def __init__(self, session):
        self.session = session

    def read_file(self, path):
        """Read the data from the given file path.
        """
        try:
            data = loadmat(path, struct_as_record=True)
        except UnicodeDecodeError as e:
            raise Oct2PyError(str(e))
        out = dict()
        for (key, value) in data.items():
            out[key] = self._extract(value)
        return out

    def _extract(self, val):
        """Parse the data from a MAT file into Pythonic objects.
        """

        # Extract each item of a list.
        if isinstance(val, list):
            return [self._extract(v) for v in val]

        # Ignore leaf objects.
        if not isinstance(val, np.ndarray):
            return val

        # Convert user defined classes.
        if hasattr(val, 'classname'):
            cls = self.session._get_user_class(val.classname)
            val = cls.from_value(val)

        # Extract struct data.
        elif val.dtype.names:
            # Singular struct
            if val.size == 1:
                out = Struct()
                for name in val.dtype.names:
                    out[name] = self._extract(val[name].squeeze().tolist())
                val = out
            # Struct array
            else:
                out = StructArray(keys=val.dtype.names)
                val = val.squeeze()
                for i in range(val.size):
                    data = Struct()
                    for (j, name) in enumerate(val.dtype.names):
                        data[name] = self._extract(val[i][j])
                    out.append(data)
                val = out

        # Extract cells.
        elif val.dtype.kind == 'O':
            val = val.squeeze().tolist()
            if not isinstance(val, list):
                val = [val]
            val = self._extract(val)

        # Compress singleton values.
        elif val.size == 1:
            val = val.item()

        # Compress empty values.
        elif val.size == 0:
            if val.dtype.kind in 'US':
                val = ''
            else:
                val = []

        # Return parsed value.
        return val

"""
.. module:: matread
   :synopsis: Read Python values from a MAT file made by Octave.
              Strives to preserve both value and type in transit.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import absolute_import, print_function, division

import numpy as np
from scipy.io import loadmat

from .compat import string_types
from .utils import Struct, Oct2PyError


class Reader(object):

    def __init__(self, session):
        self.session = session

    def read_file(self, path):
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
            return cls.from_value(val)

        # Extract struct data.
        if val.dtype.names:
            out = Struct()
            for name in val.dtype.names:
                out[name] = self._extract(val[name].squeeze().tolist())
            return out

        # Extract cells.
        if val.dtype.kind == 'O':
            val = [self._extract(v) for v in val.squeeze().tolist()]
            # Extract nested singleton strings.
            if isinstance(val[0], list) and len(val) > 1:
                out = []
                for v in val:
                    if len(v) == 1 and isinstance(v[0], string_types):
                        v = v[0]
                    out.append(v)
                val = out

            # If it contains all alike arrays, convert to an array.
            if all(isinstance(v, np.ndarray) and v.dtype == val[0].dtype
                   for v in val):
                val = np.array(val)

            return val

        # Compress scalar types.
        if val.size == 1:
            if hasattr(val, 'flatten'):
                val = val.flatten()[0]
        elif val.size == 0:
            if val.dtype.kind in 'US':
                val = ''
            else:
                val = []

        return val

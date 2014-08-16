"""
oct2py_test - Test value passing between python and Octave.

Known limitations
-----------------
* The following Numpy array types cannot be sent directly via a MAT file.  The
float16/96/128 and complex192/256 can be recast as float64 and complex128.
   ** float16('e')
   ** float96('g')
   ** float128
   ** complex192('G')
   ** complex256
   ** read-write buffer('V')
"""
import os
import sys

if not os.name == 'nt':
    # needed for testing support
    if not hasattr(sys.stdout, 'buffer'):  # pragma: no cover
        class Dummy(object):

            def write(self):
                pass
        try:
            sys.stdout.buffer = Dummy()
        except AttributeError:
            pass

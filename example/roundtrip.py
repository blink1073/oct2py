"""Send a numpy array roundtrip to Octave using an m-file.
"""
from oct2py import octave
import numpy as np

if __name__ == '__main__':
    x = np.array([[1, 2], [3, 4]], dtype=float)
    out, oclass = octave.roundtrip(x)
    # or octave.call('roundtrip', x)
    # or octave.call('roundtrip.m', x)
    # or octave.call('/path/to/roundtrip.m', x)
    import pprint
    pprint.pprint([x, x.dtype, out, oclass, out.dtype])

"""Send a numpy array roundtrip to Octave using an m-file.
"""
from oct2py import octave
import numpy as np

if __name__ == '__main__':
    x = np.array([[1, 2], [3, 4]], dtype=float)
    #use nout='max_nout' to automatically choose max possible nout
    out, oclass = octave.roundtrip(x,nout=2)
    import pprint
    pprint.pprint([x, x.dtype, out, oclass, out.dtype])

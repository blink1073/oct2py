===========
oct2py
===========

oct2py provides a bridge from python to GNU Octave. It uses Octave to run
commands and m-files.  It allows you to run any Octave function or
m-file, and passing the data seamlessly between Python and Octave using
HDF files.

If you want to run legacy m-files, don't have Matlab(R), and don't fully
trust a code translator, this is your library.

Typical usage often looks like this::

    #!/usr/bin/env python

    from oct2py import octave
    y = octave.zeros(3,3)
    help(octave.svd)
    U, S, V = octave.svd([[1, 2], [2, 3]])

# -*- coding: utf-8 -*-
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

import ctypes
import os
import sys

PY2 = sys.version[0] == "2"
PY3 = sys.version[0] == "3"


if PY2:
    unicode = unicode
    string_types = basestring
    long = long
    import Queue as queue
    from StringIO import StringIO

    input = raw_input

else:  # pragma : no cover
    unicode = str
    string_types = str
    long = int
    import queue
    from io import StringIO

    input = input


###########################
# Override the ctrl+c handler from fortran
# See http://stackoverflow.com/questions/15457786
def handler(sig):
    try:
        import _thread
    except ImportError:
        import thread as _thread
    _thread.interrupt_main()
    return 1


# This import installs the fortran ctrl+c handler
try:
    import scipy.stats

    if os.name == "nt":
        routine = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)(handler)
        ctypes.windll.kernel32.SetConsoleCtrlHandler(routine, 1)
except ImportError:
    pass

# End override for the ctrl+c handler
###########################

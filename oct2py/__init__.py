# -*- coding: utf-8 -*-
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

"""
Oct2Py is a means to seamlessly call M-files and GNU Octave functions from
Python.
It manages the Octave session for you, sharing data behind the scenes using
MAT files.  Usage is as simple as:

.. code-block:: python

    >>> import oct2py
    >>> oc = oct2py.Oct2Py()
    >>> x = oc.zeros(3,3)
    >>> print(x, x.dtype.str)  # doctest: +SKIP
    [[ 0.  0.  0.]
     [ 0.  0.  0.]
     [ 0.  0.  0.]] <f8

If you want to run legacy m-files, do not have MATLAB(TM), and do not fully
trust a code translator, this is your library.
"""
from __future__ import absolute_import, print_function, division

from .core import Oct2Py
from .io import Struct, Cell, StructArray
from .utils import get_log, Oct2PyError
from .demo import demo
from .speed_check import speed_check
from .thread_check import thread_check
from ._version import __version__

__all__ = ['Oct2Py', 'Oct2PyError', 'octave', 'Struct', 'Cell', 'StructArray',
           'demo', 'speed_check', 'thread_check', '__version__', 'get_log']

try:
    octave = Oct2Py()
except Oct2PyError as e:
    print(e)


def kill_octave():
    """Kill all octave instances (cross-platform).

    This will restart the "octave" instance.  If you have instantiated
    Any other Oct2Py objects, you must restart them.
    """
    import os
    if os.name == 'nt':
        os.system('taskkill /im octave /f')
    else:
        os.system('killall -9 octave')
        os.system('killall -9 octave-cli')
    octave.restart()

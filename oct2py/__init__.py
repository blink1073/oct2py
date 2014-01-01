# -*- coding: utf-8 -*-
"""
Oct2Py is a means to seamlessly call M-files and GNU Octave functions from Python.
It manages the Octave session for you, sharing data behind the scenes using
MAT files.  Usage is as simple as:

.. code-block:: python

    >>> import oct2py
    >>> oc = oct2py.Oct2Py() 
    >>> x = oc.zeros(3,3)
    >>> print x, x.dtype
    [[ 0.  0.  0.]
     [ 0.  0.  0.]
     [ 0.  0.  0.]] float64

If you want to run legacy m-files, do not have MATLAB(TM), and do not fully
trust a code translator, this is your library.  
"""


__title__ = 'oct2py'
__version__ = '1.3.0'
__author__ = 'Steven Silvester'
__license__ = 'MIT'
__copyright__ = 'Copyright 2013 Steven Silvester'
__all__ = ['Oct2Py', 'Oct2PyError', 'octave', 'Struct', 'demo', 'speed_test',
           'thread_test', '__version__', 'get_log']


import imp
import functools
import os

from .session import Oct2Py, Oct2PyError
from .utils import Struct, get_log
from .demo import demo
from .speed_check import speed_test
from .thread_check import thread_test


try:
    octave = Oct2Py()
except Oct2PyError as e:
    print(e)

# clean up namespace
del functools, imp, os
try:
    del session, utils, speed_check, thread_check
except NameError:  # pragma: no cover
    pass


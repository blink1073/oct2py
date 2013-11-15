# -*- coding: utf-8 -*-
"""
Oct2py is a means to seemlessly call m-files and Octave functions from python.
It manages the Octave session for you, sharing data behind the scenes using
MAT files.  Usage is as simple as:

.. code-block:: pycon

    >>> oc = oct2py.Oct2Py() 
    >>> x = oc.zeros(3,3)
    >>> print x, x.dtype
    [[ 0.  0.  0.]
     [ 0.  0.  0.]
     [ 0.  0.  0.]] float64
    ...

If you want to run legacy m-files, do not have MATLAB®, and do not fully
trust a code translator, this is your library.  
"""


__title__ = 'oct2py'
__version__ = '1.1.1'
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
    del session, utils
except NameError:  # pragma: no cover
    pass


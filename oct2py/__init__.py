# -*- coding: utf-8 -*-
"""
oct2py - Python to GNU Octave bridge.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

Overview
========
Uses Octave to run commands and m-files. Supports any Octave function or m-file,
passing the data seamlessly between Python and Octave using MAT files.
If you want to run legacy m-files, do not have MATLAB®, and do not fully
trust a code translator, this is your library.
"""
from ._oct2py import Oct2Py, Oct2PyError
try:
    from .version import version as __version__
except ImportError:
    __version__ = 'unbuilt-dev'
octave = Oct2Py()
from ._utils import Struct
from .demo import demo
from .speed_test import speed_test
from .thread_test import thread_test

__all__ = ['Oct2Py', 'Oct2PyError', 'octave', 'Struct', 'demo', 'speed_test',
          'thread_test', '__version__']

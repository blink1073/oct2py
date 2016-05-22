# -*- coding: utf-8 -*-
"""
Oct2Py is a means to seamlessly call M-files and GNU Octave functions from Python.
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

__title__ = 'oct2py'
__version__ = '3.5.7'
__author__ = 'Steven Silvester'
__license__ = 'MIT'
__copyright__ = 'Copyright 2014-2016 Steven Silvester'
__all__ = ['Oct2Py', 'Oct2PyError', 'octave', 'Struct', 'demo', 'speed_check',
           'thread_check', '__version__', 'get_log']


import imp
import functools
import os
import ctypes

try:
    import thread
except ImportError:
    import _thread as thread


if os.name == 'nt':
    """
    Allow Windows to intecept KeyboardInterrupt
    http://stackoverflow.com/questions/15457786/ctrl-c-crashes-python-after-importing-scipy-stats
    """
    basepath = imp.find_module('numpy')[1]
    try:
        lib1 = ctypes.CDLL(os.path.join(basepath, 'core', 'libmmd.dll'))
        lib2 = ctypes.CDLL(os.path.join(basepath, 'core', 'libifcoremd.dll'))

        def handler(sig, hook=thread.interrupt_main):
            hook()
            return 1

        routine = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)(handler)
        ctypes.windll.kernel32.SetConsoleCtrlHandler(routine, 1)
    except Exception:
        pass


from .core import Oct2Py, Oct2PyError
from .utils import Struct, get_log
from .demo import demo
from .speed_check import speed_check
from .thread_check import thread_check


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


# clean up namespace
del functools, imp, os, ctypes, thread

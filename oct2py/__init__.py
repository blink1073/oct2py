# -*- coding: utf-8 -*-
"""
oct2py - Python to GNU Octave bridge.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

Overview
========
Uses Octave to run commands and m-files.
Supports any Octave function or m-file,
passing the data seamlessly between Python and Octave using MAT files.
If you want to run legacy m-files, do not have MATLAB®, and do not fully
trust a code translator, this is your library.
"""
import imp
import functools
import os

from .session import Oct2Py, Oct2PyError
try:
    from .version import version as __version__
except ImportError:
    __version__ = 'unbuilt-dev'
from .utils import Struct, get_log
from .demo import demo
from .speed_test import speed_check as speed_test
from .thread_test import thread_check as thread_test

__all__ = ['Oct2Py', 'Oct2PyError', 'octave', 'Struct', 'demo', 'speed_test',
           'thread_test', '__version__', 'test', 'test_verbose', 'get_log']


octave = Oct2Py()

# The following is borrowed from the scikit-image project
#  set up a test rig
try:
    imp.find_module('nose')
except ImportError:
    def _test(verbose=False):
        """This would invoke the skimage test suite, but nose couldn't be
        imported so the test suite can not run.
        """
        raise ImportError("Could not load nose. Unit tests not available.")
else:
    def _test(verbose=False):
        """Invoke the skimage test suite."""
        import nose
        import os
        pkg_dir = os.path.abspath(os.path.dirname(__file__))
        args = ['', pkg_dir, '--exe']
        if verbose:
            args.extend(['-v', '-s'])
        nose.run('oct2py', argv=args)


# do not use `test` as function name as this leads to a recursion problem with
# the nose test suite
test = _test
test_verbose = functools.partial(test, verbose=True)
test_verbose.__doc__ = test.__doc__


# clean up namespace
del functools, imp, os
del session, utils


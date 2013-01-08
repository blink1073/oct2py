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
import imp as _imp
import functools as _functools
import os.path as _osp

from ._oct2py import Oct2Py, Oct2PyError
try:
    from .version import version as __version__
except ImportError:
    __version__ = 'unbuilt-dev'
from ._utils import Struct
from .demo import demo
from .speed_test import speed_test
from .thread_test import thread_test

__all__ = ['Oct2Py', 'Oct2PyError', 'octave', 'Struct', 'demo', 'speed_test',
          'thread_test', '__version__', 'test', 'test_verbose', 'get_log']


octave = Oct2Py()

# The following is borrowed from the scikit-image project
#  set up a test rig
try:
    _imp.find_module('nose')
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
        pkg_dir = _osp.abspath(_osp.dirname(__file__))
        args = ['', pkg_dir, '--exe']
        if verbose:
            args.extend(['-v', '-s'])
        nose.run('skimage', argv=args)


# do not use `test` as function name as this leads to a recursion problem with
# the nose test suite
test = _test
test_verbose = _functools.partial(test, verbose=True)
test_verbose.__doc__ = test.__doc__


def get_log(name=None):
    """Return a console logger.

    Output may be sent to the logger using the `debug`, `info`, `warning`,
    `error` and `critical` methods.

    Parameters
    ----------
    name : str
        Name of the log.

    References
    ----------
    .. [1] Logging facility for Python,
           http://docs.python.org/library/logging.html

    """
    import logging

    if name is None:
        name = 'pydevice'
    else:
        name = 'pydevice.' + name

    log = logging.getLogger(name)
    return log


def _setup_log():
    """Configure root logger.

    """
    import logging
    import sys

    formatter = logging.Formatter(
        '%(name)s: %(levelname)s: %(message)s'
        )

    try:
        handler = logging.StreamHandler(stream=sys.stdout)
    except TypeError:
        handler = logging.StreamHandler(strm=sys.stdout)
    handler.setFormatter(formatter)

    log = get_log()
    log.addHandler(handler)
    log.setLevel(logging.WARNING)
    log.propagate = False

_setup_log()


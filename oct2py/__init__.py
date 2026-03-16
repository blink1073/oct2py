# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

"""
Oct2Py is a means to seamlessly call M-files and GNU Octave functions from
Python.
It manages the Octave session for you, sharing data behind the scenes using
MAT files.  Usage is as simple as:

.. code-block:: pycon

    >>> import oct2py
    >>> oc = oct2py.Oct2Py()
    >>> x = oc.zeros(3, 3)
    >>> print(x, x.dtype.str)  # doctest: +SKIP
    [[ 0.  0.  0.]
     [ 0.  0.  0.]
     [ 0.  0.  0.]] <f8

If you want to run legacy m-files, do not have MATLAB(TM), and do not fully
trust a code translator, this is your library.
"""

from .utils import Oct2PyError, get_log  # noqa

from ._version import __version__
from .core import Oct2Py, OctaveWorkspaceProxy
from .demo import demo
from .io import Cell, Struct, StructArray
from .settings import Oct2PySettings
from .speed_check import speed_check
from .thread_check import thread_check

__all__ = [
    "Cell",
    "Oct2Py",
    "Oct2PyError",
    "Oct2PySettings",
    "OctaveWorkspaceProxy",
    "Struct",
    "StructArray",
    "__version__",
    "configure",
    "demo",
    "get_log",
    "octave",
    "speed_check",
    "thread_check",
]

try:
    octave = Oct2Py()
except Oct2PyError as e:
    print(e)  # noqa


def configure(settings=None, **kwargs):
    """Configure (or reconfigure) the default oct2py session.

    Parameters
    ----------
    settings : Oct2PySettings, optional
        Settings object. If not provided, one is built from kwargs and
        any OCT2PY_* environment variables.
    **kwargs
        Passed directly to Oct2PySettings (e.g. ``backend="qt"``,
        ``timeout=30``).

    Examples
    --------
    >>> import oct2py
    >>> oct2py.configure(backend="disable", timeout=30)  # doctest: +SKIP
    """
    global octave  # noqa: PLW0603
    if settings is None:
        settings = Oct2PySettings(**kwargs)
    octave.exit()
    octave = Oct2Py(settings=settings)


def kill_octave():
    """Kill all octave instances (cross-platform).

    This will restart the "octave" instance.  If you have instantiated
    Any other Oct2Py objects, you must restart them.
    """
    import os  # noqa:PLC0415

    if os.name == "nt":
        os.system("taskkill /im octave /f")  # noqa
    else:
        os.system("killall -9 octave")  # noqa
        os.system("killall -9 octave-cli")  # noqa
    octave.restart()

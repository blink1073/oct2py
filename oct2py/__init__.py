# -*- coding: utf-8 -*-
"""
oct2py - Python to GNU Octave bridge.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

Overview
========
Uses Octave to run commands and m-files. Run::

    >>> import oct2py
    >>> oct2py.demo()

for a live demo of features.  Supports any Octave function or m-file,
passing the data seamlessly between Python and Octave using MAT files.
If you want to run legacy m-files, do not have MATLAB®, and do not fully
trust a code translator, this is your library.

Installation
============
You must have GNU Octave installed and in your PATH. Additionally, you must
have the numpy and h5py libraries installed::

   python setup.py install

or::

   pip oct2py install

or::

   easy_install oct2py

Datatypes
=========
All Octave variable types are mapped to comparable Python types.  See Oct2Py
Data Conversions in the documentation for a full list.
Wherever possible, value and type are preserved on a roundtrip to Octave.
For example, if you send an ndarray of type np.int8, Octave receives an int8
matrix, and the value returned would be the original array, of type np.int8.
Almost all Python types can be sent to Octave (including ndarrays of
arbitrary rank) and read back in the same form.
Currently the library does not support nested lists with strings in them, or
an ndarray of string dtype of rank > 1.
Corner cases like sparse or empty  matrices have not been tested.
Note that dictionaries are mapped to Octave structures, which are returned
as Struct objects.  These objects behave just like an Octave struct, but
can be accessed as a dictionary as well::

       >>> from oct2py import Struct
       >>> a = Struct()
       >>> a.b = 'spam'  # a["b"] == 'spam'
       >>> a.c.d = 'eggs'  # a.c["d"] == 'eggs'
       >>> print a
       {'c': {'d': 'eggs'}, 'b': 'spam'}

Performance
===========
There is a penalty for passing data via MAT files.  Running speed_test.py
shows the effect.  After a startup time for the Octave engine (<1s),
raw function calls take almost no penalty.  The penalty for reading and
writing from the MAT file is around 10-20ms on my laptop.  This penalty is
felt  for both incoming and outgoing values.  As the data becomes
larger, the delay begins to increase (somewhere around a 100x100 array).
If you have any loops, you would be better served using a raw "run"
command for the loop rather than implementing the loop in python::

      >>> import oct2py
      >>> oct2py.speed_test()

Plotting
========
Plotting commands do not automatically result in the window being displayed
by python.  In order to force the plot to be drawn, the command
"print -deps foo.eps;'" is tacked onto anything that looks like a plot
command, when called using this package. If you have plot statements in your
function that you would like to display, you must add that line (replacing
foo.eps with the file name of your choice), after each plot statement.

Thread Safety
=============
Each instance of the Octave object has an independent session of Octave and
uses independent random MAT files. The library appears to be thread safe.
See thread_test.py for an example of several objects writing a different
value for the same variable name simultaneously and successfully retrieving
their own result::

    >>> import oct2py
    >>> oct2py.thread_test()

Future enhancements
===================
* Add a Octave code compability check function.
* Add a feature to scan a file for plot statements and automatically add a
  line to print the plot, allowing Python to render it.

Note for MATLAB® users
========================
Octave supports most but not all of the core syntax and commands.  See
http://www.gnu.org/software/octave/FAQ.html#MATLAB-compatibility. The main
noticable differences are nested functions are not allowed, and GUIs
(including uigetfile, etc.) are not supported. There are several Octave
packages (think toolboxes), including image and statistics, at
http://octave.sourceforge.net/packages.php.

Testing
=======
Unit tests are in the tests directory, and can be run individually, by
running all_tests.py, or using a test discovery tool like nose.

Similar work
============
* pytave - Python to Octave bridge, but does not run on win32 (which is the
  reason for this library).
* mlabwrap - Python to MATLAB® bridge, requires a MATLAB® license.  The
  oct2py library API is modeled after mlabwrap.
* ompc, smop - Matlab to Python conversion tools.  Both rely on effective
  parsing of code and a runtime helper library.  Ideally one or both of
  these projects render this one unnecessary.  The idea of using
  introspection and to find "nargout" was borrowed from the ompc project.

Disclaimer
==========
MATLAB® is registered trademark of The MathWorks.

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

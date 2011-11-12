''' oct2py - Python to GNU Octave bridge

Overview
--------
Uses Octave to run commands and m-files.
Run oct2py_demo.py for a live demo of features.

Supports the running of any Octave function or m-file, and passing the
data seamlessly between Python and Octave using HDF files.  

If you want to run legacy m-files, don't have Matlab(R), and don't fully trust
a code translator, this is your library.

All Octave variable types are mapped to comparable Python types.
Almost all Python types can be sent to Octave (including ndarrays),
   with the exception of cell arrays (lists with strings in them) of rank > 1.
   
Installation
------------
TDB
You must have Octave installed and in your path.  
Additionally, you must have the numpy and h5py libraries installed.

Peformance
-----------
There is a penalty for passing data via HDF files.  Running oct2py_speed.py
shows the effect.  After a startup time for the Octave engine (<1s),
raw function calls take almost no penalty.  The penalty for reading and
writing from the HDF file is around 5-10ms on my machine.  This
penalty is felt for both incoming and outgoing values.  As the data becomes
larger, the delay begins to increase (somewhere around a 100x100 array).
If you have any loops, you would be better served using a raw "run" command
for the loop rather than implementing the loop in python.

Plotting
--------
Plotting commands do not automatically result in the window being displayed
by Python.  In order to force the plot to be drawn, I have hacked the command
"print -deps foo.eps;'" onto anything that looks like a plot command, when
called using this package. If you have plot statements in your function that
you would like to display,you must add that line (replacing foo.eps
with the filename of your choice), after each plot statement.

Thread Safety
------------
Each instance of the Octave object has an independent session of Octave.
The library appears to be thread safe.  See oct2py_thread.py for an example of
several objects writing a different value for the same variable name
simultaneously and sucessfully retrieving their own result.

Future enhancements
-------------------
- Add support for arbitrary outgoing cell arrays (rank > 1)
- Add a Octave code compability check function
- Add a feature to scan a file for plot statements and automatically
     add a line to print the plot, allowing Python to render it.

Note for Matlab(R) users
------------------------
Octave supports most but not all of the core syntax
and commands.  See:
    http://www.gnu.org/software/octave/FAQ.html#MATLAB-compatibility

The main noticable differences are nested functions are not allowed,
  and GUIs (including uigetfile, etc.) are not supported.

There are several Octave packages (think toolboxes),
    including image and statistics:
    http://octave.sourceforge.net/packages.php

Similar work
------------
pytave - Python to Octave bridge, but does not run on Windows (which is
             why I made this one).
mlabwrap - Python to Matlab bridge, requires a Matlab license.  I based
            my API on theirs.
ompc, smop - Matlab to Python conversion tools.  Both rely on effective
             parsing of code and a runtime helper library.  I would
             love to see one or both of these projects render this one
             unnecessary.  I borrowed the idea from ompc of using
             introspection to find "nargout" dynamically.
'''
from _oct2py import Oct2Py, Oct2PyError

octave = Oct2Py()

from _utils import Struct

from demo import demo

from speed_test import speed_test

from thread_test import thread_test

__all__ = ['Oct2Py', 'Oct2PyError', 'octave', 'Struct', 'demo', 'speed_test',
          'thread_test']

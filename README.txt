====================================
oct2py - Python to GNU Octave bridge
====================================

Overview
========
Uses Octave to run commands and m-files. Run demo.py for a live demo of
features.

Supports the running of any Octave function or m-file, and passing the data
seamlessly between Python and Octave using HDF files.

If you want to run legacy m-files, do not have MATLAB®, and don't fully trust
a code translator, this is your library.

Datatypes
=========
All Octave variable types are mapped to comparable Python types.  If you pull
tests/test_datatypes.m into your working directory and try the following::

    from oct2py import octave
    out = octave.test_datatypes()

You can compare the variables in the "out" variable to the ones in
test_datatypes.m.  These variable values and types are preserved on a
roundtrip to Octave (e.g. writing passing an int8 ndarray to Octave and reading
back the result gives an int8 ndarray with the same values.

Almost all Python types can be sent to Octave (including ndarrays of arbitrary
rank) and read back in the same form.  The exceptions of nested lists with
strings in them, or an ndarray with 'S' type fields.  I have not yet tested
corner cases like sparse or empty  matrices.

Installation
============
pip install oct2py
You must have GNU Octave installed and in your PATH.
Additionally, you must have the numpy and h5py libraries installed
(pip will actually install these for you, unless you are on a Unix machine and
do not have the required HDF libaries installed).

Peformance
==========
There is a penalty for passing data via HDF files.  Running speed_test.py
shows the effect.  After a startup time for the Octave engine (<1s),
raw function calls take almost no penalty.  The penalty for reading and
writing from the HDF file is around 5-10ms on my machine.  This
penalty is felt for both incoming and outgoing values.  As the data becomes
larger, the delay begins to increase (somewhere around a 100x100 array).
If you have any loops, you would be better served using a raw "run" command
for the loop rather than implementing the loop in python.

Plotting
========
Plotting commands do not automatically result in the window being displayed
by Python.  In order to force the plot to be drawn, I have hacked the command
"print -deps foo.eps;'" onto anything that looks like a plot command, when
called using this package. If you have plot statements in your function that
you would like to display,you must add that line (replacing foo.eps
with the filename of your choice), after each plot statement.

Thread Safety
=============
Each instance of the Octave object has an independent session of Octave.
The library appears to be thread safe.  See thread_test.py for an example of
several objects writing a different value for the same variable name
simultaneously and sucessfully retrieving their own result.

Future enhancements
===================
- Add support for arbitrary outgoing cell arrays (rank > 1)
- Add a Octave code compability check function
- Add a feature to scan a file for plot statements and automatically
     add a line to print the plot, allowing Python to render it.

Note for MATLAB® users
========================
Octave supports most but not all of the core syntax
and commands.  See:
    http://www.gnu.org/software/octave/FAQ.html#MATLAB-compatibility

The main noticable differences are nested functions are not allowed,
  and GUIs (including uigetfile, etc.) are not supported.

There are several Octave packages (think toolboxes),
    including image and statistics:
    http://octave.sourceforge.net/packages.php

Testing
=======
Unit tests are in the tests directory, and can be run individually, by
running all_tests.py, or using a test discovery tool like nose.

Similar work
============
* pytave - Python to Octave bridge, but does not run on win32 (which is
             why I made this one).
* mlabwrap - Python to MATLAB® bridge, requires a MATLAB® license.  I based
            my API on theirs.
* ompc, smop - Matlab to Python conversion tools.  Both rely on effective
             parsing of code and a runtime helper library.  I would
             love to see one or both of these projects render this one
             unnecessary.  I borrowed the idea from ompc of using
             introspection to find "nargout" dynamically.

MATLAB® is registered trademark of The MathWorks.

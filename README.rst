oct2py - Python to GNU Octave bridge.

Overview
========
Uses Octave to run commands and m-files. Run::

    >>> import oct2py
    >>> oct2py.demo()

for a live demo of features.  Supports any Octave function or m-file,
passing the data seamlessly between Python and Octave using MAT files.
If you want to run legacy m-files, do not have MATLAB®, and do not fully
trust a code translator, this is your library.


New in Version 0.4
====================
- Added a restart method to Oct2Py objects to start a clean session
- Added get_log and test methods to oct2py
- Support for sparse arrays (scipy.sparse.csc.csc_matrix)
- Improvements to octave cell type handling
- Some bugfixes and testing improvements


Installation
============
You must have GNU Octave installed and in your PATH. On Windows, the easiest
way to get Octave is to use an installer from:
http://sourceforge.net/projects/octave/files/Octave%20Windows%20binaries/.
On Linux, it should be available from your package manager.
Additionally, you must have the numpy and scipy libraries installed, then run::

   python setup.py install

or::

   pip install oct2py

or::

   easy_install oct2py

Note for Windows users: You may have to follow the instructions at:
http://wiki.octave.org/Octave_for_Windows#Printing_.28installing_Ghostscript.29
in order to use inline figures in IPython (or specify -f svg).


Datatypes
=========
All Octave variable types are mapped to comparable Python types.  See Oct2Py
Data Conversions in the documentation for a full list.
Wherever possible, value and type are preserved on a roundtrip to Octave.
For example, if you send an ndarray of type np.int8, Octave receives an int8
matrix, and the value returned would be the original array, of type np.int8.
Almost all Python types can be sent to Octave (including ndarrays of
arbitrary rank) and read back in the same form.
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
shows the effect.  After a startup time for the Octave engine (<1s typically),
raw function calls take almost no penalty.  The penalty for reading and
writing from the MAT file is around 1-2ms on my laptop.  This penalty is
felt for both incoming and outgoing values.  As the data becomes
larger, the delay begins to increase (somewhere around a 100x100 array).
If you have any loops, you would be better served using a raw "run"
command for the loop rather than implementing the loop in python::

      >>> import oct2py
      >>> oct2py.speed_test()

Plotting
========
Plotting commands do not automatically result in the window being displayed
by python.  In order to force the plot to be drawn, the command
"figure(gcf() + 1);'" is tacked onto anything that looks like a plot
command, when called using this package. If you have plot statements in your
function that you would like to display, you must add that line
after each plot statement.


Thread Safety
=============
Each instance of the Octave object has an independent session of Octave and
uses independent random MAT files. The library therefore should be thread safe.
See thread_test.py for an example of several objects writing a different
value for the same variable name simultaneously and successfully retrieving
their own result::

    >>> import oct2py
    >>> oct2py.thread_test()

Future enhancements
===================
* Add an Octave code compability check function
* Add a feature to scan a file for plot statements and automatically add a
  line to show the figure.

Note for MATLAB® users
========================
Octave supports most but not all of the core syntax and commands.  See
http://www.gnu.org/software/octave/FAQ.html#MATLAB-compatibility. The main
noticable differences are nested functions are not allowed, and GUIs
(including uigetfile, etc.) are not supported. There are several Octave
packages (think toolboxes), including image and statistics, at
http://octave.sourceforge.net/packages.php.

Similar work
============
* pytave - Python to Octave bridge, but does not run on win32 (which is the
  reason for this library).
* mlabwrap - Python to MATLAB® bridge, requires a MATLAB® license.  The
  oct2py library API is modeled after mlabwrap.
* ompc, smop - Matlab to Python conversion tools.  Both rely on effective
  parsing of code and a runtime helper library.  Ideally one or both of
  these projects render this one unnecessary.  The idea of using
  introspection to find "nargout" was borrowed from the ompc project.

CI Status
=========

**oct2py** has automatic testing enabled through the convenient
`Travis CI project <https://travis-ci.org>`_. Here is the latest build status:

.. image:: https://travis-ci.org/blink1073/oct2py.png?branch=master
  :align: center
  :target: https://travis-ci.org/blink1073/oct2py

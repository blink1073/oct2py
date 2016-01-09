Oct2Py: Python to GNU Octave Bridge
===================================

.. image:: https://badge.fury.io/py/oct2py.png/
    :target: http://badge.fury.io/py/oct2py

.. image:: https://pypip.in/d/oct2py/badge.png
        :target: https://crate.io/packages/oct2py/

.. image:: https://coveralls.io/repos/blink1073/oct2py/badge.png?branch=master
  :target: https://coveralls.io/r/blink1073/oct2py


Oct2Py is a means to seamlessly call M-files and Octave functions from Python.
It manages the Octave session for you, sharing data behind the scenes using
MAT files.  Usage is as simple as:

.. code-block:: python

    >>> oc = oct2py.Oct2Py()
    >>> x = oc.zeros(3,3)
    >>> print(x, x.dtype)
    [[ 0.  0.  0.]
     [ 0.  0.  0.]
     [ 0.  0.  0.]] float64
    ...

If you want to run legacy m-files, do not have MATLAB(TM), and do not fully
trust a code translator, this is your library.


Features
--------

- Supports all Octave datatypes and most Python datatypes and Numpy dtypes.
- Provides OctaveMagic_ for IPython, including inline plotting in notebooks.
- Supports cell arrays and structs with arbitrary nesting.
- Supports sparse matrices.
- Builds methods on the fly linked to Octave commands (e.g. `zeros` above).
- Nargout is automatically inferred by the number of return variables.
- Thread-safety: each Oct2Py object uses an independent Octave session.
- Can be used as a context manager.
- Supports Unicode characters.
- Supports logging of session commands.
- Optional timeout command parameter to prevent runaway Octave sessions.


.. _OctaveMagic: http://nbviewer.ipython.org/github/blink1073/oct2py/blob/master/example/octavemagic_extension.ipynb?create=1


Installation
------------
You must have GNU Octave 3.6 or newer installed and in your PATH.
On Windows, the easiest way to get Octave is to use an installer from SourceForge_.
You must have the Numpy and Scipy libraries installed.
On Linux, it should be available from your package manager.
You can specify the path to your Octave executable by creating an `OCTAVE_EXECUTABLE` environmental variable.

To install Oct2Py, simply:

.. code-block:: bash

    $ pip install oct2py


Documentation
-------------

Documentation is available online_.

For version information, see the Revision History_.


.. _SourceForge: http://sourceforge.net/projects/octave/files/Octave%20Windows%20binaries/

.. _online: http://blink1073.github.io/oct2py/

.. _History: https://github.com/blink1073/oct2py/blob/master/HISTORY.rst

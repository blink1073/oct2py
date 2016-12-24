Oct2Py: Python to GNU Octave Bridge
===================================

.. image:: https://badge.fury.io/py/oct2py.png/
    :target: http://badge.fury.io/py/oct2py

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


Installation
------------
You must have GNU Octave 3.6 or newer installed and in your PATH.
You must have the Numpy and Scipy libraries for Python installed.
See the installation instructions_ for more details.

Once the dependencies have been installed, run:

.. code-block:: bash

    $ pip install oct2py

If using conda, it is available on conda-forge:

.. code-block:: bash
   
   $ conda install -c conda-forge oct2py


Documentation
-------------

Documentation is available online_.

For version information, see the Revision History_.


.. _OctaveMagic: http://nbviewer.ipython.org/github/blink1073/oct2py/blob/master/example/octavemagic_extension.ipynb?create=1

.. _instructions: http://blink1073.github.io/oct2py/source/installation.html

.. _online: http://blink1073.github.io/oct2py/

.. _History: https://github.com/blink1073/oct2py/blob/master/HISTORY.rst

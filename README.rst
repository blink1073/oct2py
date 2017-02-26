Oct2Py: Python to GNU Octave Bridge
===================================

.. image:: https://badge.fury.io/py/oct2py.png/
    :target: http://badge.fury.io/py/oct2py

.. image:: https://codecov.io/github/blink1073/oct2py/coverage.svg?branch=master
  :target: https://codecov.io/github/blink1073/oct2py?branch=master

Oct2Py allows you to seamlessly call M-files and Octave functions from Python.
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

If you want to run legacy m-files, do not have MATLAB®, and do not fully
trust a code translator, this is your library.


Features
--------

- Supports all Octave datatypes and most Python datatypes and Numpy dtypes.
- Provides OctaveMagic_ for IPython, including inline plotting in notebooks.
- Supports cell arrays and structs/struct arrays with arbitrary nesting.
- Supports sparse matrices.
- Builds methods on the fly linked to Octave commands (e.g. `zeros` above).
- Thread-safety: each Oct2Py object uses an independent Octave session.
- Can be used as a context manager.
- Supports Unicode characters.
- Supports logging of session commands.
- Optional timeout command parameter to prevent runaway Octave sessions.


.. _OctaveMagic: http://nbviewer.jupyter.org/github/blink1073/oct2py/blob/master/example/octavemagic_extension.ipynb?create=1


Installation
------------
You must have GNU Octave installed and in your ``PATH``.
You must have the Numpy and Scipy libraries for Python installed.
See the installation instructions_ for more details.

Once the dependencies have been installed, run:

.. code-block:: bash

    $ pip install oct2py

If using conda, it is available on conda-forge:

.. code-block:: bash
   
   $ conda install -c conda-forge oct2py

.. _instructions: http://blink1073.github.io/oct2py/source/installation.html


Documentation
-------------

Documentation is available online_.

For version information, see the Revision History_.

.. _online: http://blink1073.github.io/oct2py/

.. _History: https://github.com/blink1073/oct2py/blob/master/HISTORY.rst

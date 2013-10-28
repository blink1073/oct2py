Oct2py: Python to GNU Octave Bridge
===================================

.. image:: https://badge.fury.io/py/oct2py.png
    :target: http://badge.fury.io/py/oct2py

.. image:: https://pypip.in/d/oct2py/badge.png
        :target: https://crate.io/packages/oct2py/

.. image:: https://coveralls.io/repos/blink1073/oct2py/badge.png
  :target: https://coveralls.io/r/blink1073/oct2py


Oct2py is a means to seemlessly call m-files and Octave functions from python.
It manages the Octave session for you, sharing data behind the scenes using
MAT files.  Usage is as simple as:

.. code-block:: pycon

    >>> oc = oct2py.Oct2Py() 
    >>> x = oc.zeros(3,3)
    >>> print x, x.dtype
    [[ 0.  0.  0.]
     [ 0.  0.  0.]
     [ 0.  0.  0.]] float64
    ...

If you want to run legacy m-files, do not have MATLAB®, and do not fully
trust a code translator, this is your library.  


Features
--------

- Supports all Octave datatypes and most python datatypes and numpy dtypes.
- Provides %octavemagic% for IPython, including inline plotting in notebooks.
- Supports cell arrays and structs with arbitrary nesting.
- Supports sparse matrices.
- Builds methods on the fly linked to Octave commands (e.g. `zeros` above).
- Nargout is automatically inferred by the number of return variables.
- Thread-safety - each Oct2Py object uses an independent Octave session.
- Can be used as a context manager.
- Supports unicode characters.


Installation
------------
You must have GNU Octave installed and in your PATH. On Windows, the easiest
way to get Octave is to use an installer from `sourceforge <http://sourceforge.net/projects/octave/files/Octave%20Windows%20binaries/>`_.
On Linux, it should be available from your package manager.
Additionally, you must have the numpy and scipy libraries installed.

To install Oct2py, simply:

.. code-block:: bash

    $ pip install oct2py

Or, if you absolutely must:

.. code-block:: bash

    $ easy_install oct2py


Documentation
-------------

Documentation is available at http://pythonhosted.org/oct2py/.


Installation
============
You must have GNU Octave installed and in your PATH. On Windows, the easiest
way to get Octave is to use an installer from `sourceforge <http://sourceforge.net/projects/octave/files/Octave%20Windows%20binaries/>`_.
On Linux, it should be available from your package manager.
Additionally, you must have the numpy and scipy libraries installed, then run::

   python setup.py install

or::

   pip install oct2py

or::

   easy_install oct2py

Note for Windows users: You may have to follow these `instructions <http://wiki.octave.org/Octave_for_Windows#Printing_.28installing_Ghostscript.29>`_
in order to use inline figures in IPython (or specify -f svg).


******************
Information
******************

Octave Session Interaction
==========================
Oct2Py has an `interact` method (essentially the Octave keyboard function), 
that drops you into an interactive Octave prompt in the current session.
The keyboard function also works, even if it is in an m-file.  

Note: If you are on Linux, you must have pexpect installed, or Oct2Py will
hang on any keyboard call and the `interact` method will raise and error.


Syntax Errors
=============
An Octave Syntax Error will result in the Octave Session being closed 
*unless* you are on Linux and have `pexpect` installed.  This is because Octave
is expecting a tty connection (which pexpect emulates).
  

Graphics Toolkit
================
Oct2Py uses the `gnuplot` graphics toolkit by default.  To change toolkits:

.. code-block:: python

    >>> from oct2py import octave
    >>> octave.available_graphics_toolkits()
    [u'fltk', u'gnuplot']
    >>> octave.graphics_toolkit('fltk')
    

Context Manager
===============
Oct2Py can be used as a Context Manager.  The session will be closed and the
temporary m-files will be deleted when the Context Manager exits.

.. code-block:: python

    >>> from oct2py import Oct2Py
    >>> with Oct2Py() as oc:
    >>>     oc.ones(10)
    

Logging
=======
Oct2Py supports logging of session interaction.  You can provide a logger
to the constructor or set one at any time.

.. code-block:: python

    >>> import logging
    >>> from oct2py import Oct2Py, get_log
    >>> oc = Oct2Py(logger=get_log())
    >>> oc.logger = get_log('new_log')
    >>> oc.logger.setLevel(logging.INFO)


Shadowed Function Names
=======================
If you'd like to call an Octave function that is also an Oct2Py method, 
you must add a trailing underscore. For example:

.. code-block:: python

    >>> from oct2py import octave
    >>> fig = octave.figure()
    >>> octave.close_(fig)


Structs
=======
Struct is a convenience class that mimics an Octave structure variable type.
It is a dictionary with attribute lookup, and it creates sub-structures on the
fly.  It can be pickled.

.. code-block:: python

    >>> from oct2py import Struct
    >>> test = Struct()
    >>> test['foo'] = 1
    >>> test.bizz['buzz'] = 'bar'
    >>> test
    {'foo': 1, 'bizz': {'buzz': 'bar'}}
    >>> import pickle
    >>> p = pickle.dumps(test)

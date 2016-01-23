
******************
Information
******************

Dynamic Functions
=================
Oct2Py will create methods for you on the fly, which correspond to Octave
functions.  For example:

.. code-block:: python

    >>> from oct2py import octave
    >>> octave.ones(3)
    array([[ 1.,  1.,  1.],
       [ 1.,  1.,  1.],
       [ 1.,  1.,  1.]])


If you pass keyword arguments to the function, they will be treated as
Octave keywords, for example, `octave.plot(x, y, linewidth=3)` becomes
`plot(x, y, 'linewidth', 3)`.  Arguments that are integer type will be converted to floats unless you set `convert_to_float=False`.

Additionally, you can look up the documentation for one of these methods using
`help()`

.. code-block:: python

    >>> help(octave.ones)
    'ones' is a built-in function
    ...

Interactivity
=============
Oct2Py supports code completion in IPython, so once you have created a method,
you can recall it on the fly, so octave.one<TAB> would give you ones.
Structs (mentioned below) also support code completion for attributes.

You can share data with an Octave session explicitly using the `push` and
`pull` methods.  When using other Oct2Py methods, the variable names in Octave
start with underscores because they are temporary (you would only see this if
you were using logging).

.. code-block:: python

    >>> from oct2py import octave
    >>> octave.push('a', 1)
    >>> octave.pull('a')
    1


Using M-Files
=============
In order to use an m-file in Oct2Py you must first call `addpath`
for the directory containing the script.  You can then use it as
a dynamic function or use the `eval` function to call it.

.. code-block:: python

    >>> from oct2py import octave
    >>> octave.addpath('/path/to/')
    >>> octave.myscript(1, 2)
    >>> # or
    >>> octave.eval("myscript(1, 2)")


Direct Interaction
==================
Oct2Py supports the Octave `keyboard` function
which drops you into an interactive Octave prompt in the current session.
This also works in the IPython Notebook.  Note: If you use the `keyboard` command and the session hangs, try opening an Octave session from your terminal and see if the `keyboard` command hangs there too.  You may need to update your version of Octave.


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

All Oct2Py methods support a `verbose` keyword.  If True, the commands are
logged at the INFO level, otherwise they are logged at the DEBUG level.


Shadowed Function Names
=======================
If you'd like to call an Octave function that is also an Oct2Py method,
you must add a trailing underscore. For example:

.. code-block:: python

    >>> from oct2py import octave
    >>> octave.eval_('a=1')
    'a =  1'

The methods that shadow Octave builtins are: `exit` and `eval`.


Timeout
=======
Oct2Py sessions have a `timeout` attribute that determines how long to wait
for a command to complete.  The default is 1e6 seconds (indefinite).
You may either set the timeout for the session, or as a keyword
argument to an individual command.  The session is closed in the event of a
timeout.


.. code-block:: python

    >>> from oct2py import octave
    >>> octave.timeout = 3
    >>> octave.sleep(2)
    >>> octave.sleep(2, timeout=1)
    Traceback (most recent call last):
    ...
    oct2py.utils.Oct2PyError: Session timed out


Graphics Toolkit
================
Oct2Py uses the `gnuplot` graphics toolkit by default.  Fltk has been known
not to work on some systems.  To change toolkits:

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


Nargout
=======
Oct2Py handles nargout the same way that Octave would (which is not how it
normally works in Python).  The number return variables affects the
behavior of the Octave function.  For example, the following two calls to SVD
return different results:

.. code-block:: python

    >>> from oct2py import octave
    >>> out = octave.svd(np.array([[1,2], [1,3]])))
    >>> U, S, V = octave.svd([[1,2], [1,3]])


Structs
=======
Struct is a convenience class that mimics an Octave structure variable type.
It is a dictionary with attribute lookup, and it creates sub-structures on the
fly of arbitrary nesting depth.  It can be pickled. You can also use tab
completion for attributes when in IPython.

.. code-block:: python

    >>> from oct2py import Struct
    >>> test = Struct()
    >>> test['foo'] = 1
    >>> test.bizz['buzz'] = 'bar'
    >>> test
    {'foo': 1, 'bizz': {'buzz': 'bar'}}
    >>> import pickle
    >>> p = pickle.dumps(test)


Unicode
=======
Oct2Py supports Unicode characters, so you may feel free to use m-files that
contain them.


Speed
=====
There is a performance penalty for passing information using MAT files.
If you have a lot of calculations, it is probably better to make an m-file
that does the looping and data aggregation, and pass that back to Python
for further processing.  To see an example of the speed penalty on your
machine, run:

.. code-block:: python

    >>> import oct2py
    >>> oct2py.speed_check()


Threading
=========
If you want to use threading, you *must* create a new `Oct2Py` instance for
each thread.  The `octave` convenience instance is in itself *not* threadsafe.
Each `Oct2Py` instance has its own dedicated Octave session and will not
interfere with any other session.


IPython Notebook
================
Oct2Py provides OctaveMagic_ for IPython, including inline plotting in
notebooks.  This requires IPython >= 1.0.0.

.. _OctaveMagic: http://nbviewer.ipython.org/github/blink1073/oct2py/blob/master/example/octavemagic_extension.ipynb?create=1




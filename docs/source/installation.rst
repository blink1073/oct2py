Installation
************************

Library Installation
--------------------
You must have GNU Octave installed and in your PATH
(see instructions below).  The library is only known to work with
Octave 4.0+.
Additionally, you must have the Numpy and Scipy libraries for Python
installed.
The simplest way to get them is to use the Anaconda_ distribution.

Once the dependencies have been installed, run:

.. code-block:: bash

    $ pip install oct2py

If using conda, it is available on conda-forge:

.. code-block:: bash

   $ conda install -c conda-forge oct2py


GNU Octave Installation
-----------------------
- On Linux platforms, try your package manager, or follow the
  instructions from Octave_.  You must also have gnuplot installed, and
  gnuplot-x11 or gnuplot-qt, if available.

- On OSX, the recommended methods are listed on this wiki_.

- On Windows, download the latest MinGW or .NET version_.  Cygwin
  is *NOT* supported.
  The MinGW version requires the 7zip_ program for installation.
  Make sure to install gnuplot if prompted.
  Finally, to add Octave to your path. You can do so from the Environmental
  Variables dialog for your version of Windows, or set from the command prompt::

      setx PATH "%PATH%;<path-to-octave-dir>

  Where the folder <path-to-octave-dir> has the file "octave.exe".
  If you see the message: "WARNINGS: The data being saved is truncated to 1024 characters"
  It means your PATH variable is too long.  You'll have to manually trim in in the Windows
  Environmental Variables editor.

- To test, open a command window (or terminal) and type: ``octave``.
  If Octave starts, you should be good to go.

- Alternatively, you can specify the path to your Octave executable by
  creating an ``OCTAVE_EXECUTABLE`` environmental variable.

Graphics Backend (Qt vs gnuplot)
---------------------------------
By default, oct2py runs ``octave-cli``, which only supports the ``gnuplot``
backend (or ``fltk`` in some cases) and has limited support for rendering or
interactive plots.  On newer versions of Octave, the ``qt`` graphics toolkit
is only available when Octave is started with a display.

To use the ``qt`` backend for rendering or interactive plots, set
``OCTAVE_EXECUTABLE`` to ``octave`` or the path to your Octave executable:

.. code-block:: bash

    $ export OCTAVE_EXECUTABLE=octave

On remote or headless systems you can use a virtual framebuffer:

.. code-block:: bash

    $ export OCTAVE_EXECUTABLE="xvfb-run octave"

.. _Anaconda: https://conda.io/projects/conda/en/latest/user-guide/install/index.html
.. _pip: http://www.pip-installer.org/en/latest/installing.html
.. _Octave:  https://octave.org/doc/interpreter/Installation.html
.. _wiki: http://wiki.octave.org/Octave_for_MacOS_X
.. _version: https://sourceforge.net/projects/octave/files/Octave%20Windows%20binaries/
.. _7zip: https://portableapps.com/apps/utilities/7-zip_portable

Installation for Oct2Py
************************

Library Installation
--------------------
You must have GNU Octave installed and in your PATH (see instructions below).
Additionally, you must have the numpy and scipy libraries installed.  On Windows, you can get the binaries here_. Install this libary via::

   python setup.py install

or::

   pip oct2py install

or::

   easy_install oct2py


.. _here: http://scipy.org/Download


GNU Octave Installation
-----------------------
- On linux platforms, try your package manager, or follow the
  instructions from Octave_.

.. _Octave:  http://www.gnu.org/software/octave/doc/interpreter/Installation.html

- On Windows, download the latest MinGW or .NET version_.
  You will need a 7zip_ program.
  Finally, to add to your path you can find the Environmental  Variables dialog for your version of Windows, or set from the command prompt::

      setx PATH "%PATH%;<path-to-octave-bin-dir>

.. _version: http://sourceforge.net/projects/octave/files/Octave%20Windows%20binaries/
.. _7zip: http://portableapps.com/apps/utilities/7-zip_portable
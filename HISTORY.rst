.. :changelog:

Release History
---------------

1.5.0 (2014-07-03)
++++++++++++++++++
- Removed optional pexpect dependency
- Brought back support for Python 2.6


1.4.0 (2014-06-28)
++++++++++++++++++
- Added support for Python 3.4 and Octave 3.8
- Support long_field names
- Dropped support for Python 3.2


1.3.0 (2014-01-20)
++++++++++++++++++
- Added support for Octave keyboard function (requires pexpect on Linux).
- Improved error messages when things go wrong in the Octave session
- (Linux) When pexpect is installed, Octave no longer closes session when
  a Syntax Error is encountered.
- Fixed: M-files with no docstrings are now supported.


1.2.0 (2013-12-14)
++++++++++++++++++
- OctaveMagic is now part of Oct2Py: ``%load_ext oct2py.ipython``
- Enhanced Struct behavior - supports REPL completion and pickling
- Fixed: Oct2Py will install on Python3 when using setup.py


1.1.1 (2013-11-14)
++++++++++++++++++
- Added support for wheels.
- Fixed: Put docs back in the manifest.
- Fixed: Oct2py will install when there is no Octave available.


1.1.0 (2013-10-27)
++++++++++++++++++

- Full support for plotting with no changes to user code
- Support for Nargout = 0
- Overhaul of front end documentation
- Improved test coverage and added badge.
- Supports Python 2 and 3 from a single code base.
- Fixed: Allow help(Oct2Py()) and tab completion on REPL
- Fixed: Allow tab completion for Oct2Py().<TAB> in REPL


1.0.0 (2013-10-4)
+++++++++++++++++

- Support for Python 3.3
- Added logging to Oct2Py class with optional logger keyword
- Added context manager
- Added support for unicode characters
- Improved support for cell array and sparse matrices
- Fixed: Changes to user .m files are now refreshed during a session
- Fixed: Remove popup console window on Windows


0.4.0 (2013-01-05)
++++++++++++++++++

- Singleton elements within a cell array treated as a singleton list
- Added testing on 64 bit architecture
- Fixed:  Incorrect Octave commands give a more sensible error message


0.3.6 (2012-10-08)
++++++++++++++++++

- Default Octave working directory set to same as OS working dir
- Fixed: Plot rending on older Octave versions


0.3.4 (2012-08-17)
++++++++++++++++++

- Improved speed for larger matrices, better handling of singleton dimensions


0.3.0 (2012-06-16)
++++++++++++++++++

- Added Python 3 support
- Added support for numpy object type


0.2.1 (2011-11-25)
++++++++++++++++++

- Added Sphinx documentation


0.1.4 (2011-11-15)
++++++++++++++++++

- Added support for pip


0.1.0 (2011-11-11)
++++++++++++++++++

- Initial Release

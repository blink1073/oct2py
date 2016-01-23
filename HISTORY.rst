.. :changelog:

Release History
---------------

3.5.0 (2016-01-23)
++++++++++++++++++
- Disable --braindead Octave argument.


3.4.0 (2016-01-09)
++++++++++++++++++
- Improved handling of Octave executable

3.3.0 (2015-07-16)
++++++++++++++++++
- Support for Octave 4.0
- Fixes for corner cases on structs


3.2.0 (2015-06-18)
++++++++++++++++++
- Better handling of returned empty values
- Allow OCTAVE environment variable


3.1.0 (2015-02-13)
++++++++++++++++++
- Fix handling of temporary files for multiprocessing
- Clean up handling of plot settings


3.0.0 (2015-01-10)
++++++++++++++++++
- Add `convert_to_float` property that is True by default.
- Suppress output in dynamic function calls (using ';')


2.4.2 (2014-12-19)
++++++++++++++++++
- Add support for Octave 3.8 on Windows

2.4.1 (2014-10-22)
++++++++++++++++++
- Prevent zombie octave processes.

2.4.0 (2014-09-27)
++++++++++++++++++
- Make `eval` output match Octave session output.
  If verbose=True, print all Octave output.
  Return the last "ans" from Octave, if available.
  If you need the response, use `return_both` to get the
  `(resp, ans)` pair back
- As a result of the previous, Syntax Errors in Octave code
  will now result in a closed session on Windows.
- Fix sizing of plots when in inline mode.
- Numerous corner case bug fixes.


2.3.0 (2014-09-14)
++++++++++++++++++
- Allow library to install without meeting explicit dependencies
- Fix handling of cell magic with inline comments.


2.2.0 (2014-09-14)
++++++++++++++++++
- Fix IPython notebook support in Ubuntu 14.04
- Fix toggling of inline plotting


2.1.0 (2014-08-23)
++++++++++++++++++
- Allow keyword arguments in functions: `octave.plot([1,2,3], linewidth=2))`
  These are translated to ("prop", value) arguments to the function.
- Add option to show plotting gui with `-g` flag in OctaveMagic.
- Add ability to specify the Octave executable as a keyword argument to
  the Oct2Py object.
  - Add specifications for plot saving instead of displaying plots to `eval` and
    dynamic functions.


2.0.0 (2014-08-14)
++++++++++++++++++
- **Breaking changes**
 -- Removed methods: `run`, `call`, `lookfor`
 -- Renamed methods: `_eval` -> `eval`, `get` -> `pull`, `put` -> `push`,
    `close` -> `exit`
 -- Removed run and call in favor of using eval dynamic functions.
 -- Renamed methods to avoid overshadowing Octave builtins and for clarity.
 -- When a command results in "ans", the value of "ans" is returned
    instead of the printed string.
- Syntax Errors on Windows no longer crash the session.
- Added ability to interrupt commands with CTRL+C.
- Fixed Octavemagic not following current working directory.


1.6.0 (2014-07-26)
++++++++++++++++++
- Added 'temp_dir' argument to Oct2Py constructor (#50)
- Added 'kill_octave' convenience method to kill zombies (#46)
- Improved Octave shutdown handling (#45, #46)
- Added 'oned_as' argument to Oct2Py constructor (#49)


1.5.0 (2014-07-01)
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

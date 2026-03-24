# Oct2Py: Python to GNU Octave Bridge

[![PyPI version](https://badge.fury.io/py/oct2py.png/)](https://badge.fury.io/py/oct2py)
[![codecov](https://codecov.io/github/blink1073/oct2py/coverage.svg?branch=main)](https://codecov.io/github/blink1073/oct2py?branch=main)
[![PyPi Download stats](https://pepy.tech/badge/oct2py)](https://pepy.tech/project/oct2py)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/blink1073/oct2py/main?filepath=example/octavemagic_extension.ipynb)

Oct2Py allows you to seamlessly call M-files and Octave functions from Python.
It manages the Octave session for you, sharing data behind the scenes using
MAT files. Usage is as simple as:

```python
>>> import oct2py
>>> oc = oct2py.Oct2Py()
>>> x = oc.zeros(3, 3)
>>> print(x, x.dtype)
[[0. 0. 0.]
 [0. 0. 0.]
 [0. 0. 0.]] float64
```

To run .m function, you need to explicitly add the path to .m file using:

```python
>>> from oct2py import octave
>>> # to add a folder use:
>>> octave.addpath("/path/to/directory")  # doctest: +SKIP
>>> # to add folder with all subfolder in it use:
>>> octave.addpath(octave.genpath("/path/to/directory"))  # doctest: +SKIP
>>> # to run the .m file :
>>> octave.run("fileName.m")  # doctest: +SKIP
```

To get the output of .m file after setting the path, use:

```python
>>> import numpy as np
>>> from oct2py import octave
>>> x = np.array([[1, 2], [3, 4]], dtype=float)
>>> # use nout='max_nout' to automatically choose max possible nout
>>> octave.addpath("./example")  # doctest: +SKIP
>>> out, oclass = octave.roundtrip(x, nout=2)  # doctest: +SKIP
>>> import pprint  # doctest: +SKIP
>>> pprint.pprint([x, x.dtype, out, oclass, out.dtype])  # doctest: +SKIP
[array([[1., 2.],
        [3., 4.]]),
    dtype('float64'),
    array([[1., 2.],
        [3., 4.]]),
    'double',
    dtype('<f8')]
```

If you want to run legacy m-files, do not have MATLAB®, and do not fully
trust a code translator, this is your library.

## Features

- Supports all Octave datatypes and most Python datatypes and Numpy dtypes.
- Provides [OctaveMagic](https://nbviewer.org/github/blink1073/oct2py/blob/main/example/octavemagic_extension.ipynb?create=1) for IPython, including inline plotting in notebooks.
- Supports cell arrays and structs/struct arrays with arbitrary nesting.
- Supports sparse matrices.
- Builds methods on the fly linked to Octave commands (e.g. `zeros` above).
- Thread-safety: each Oct2Py object uses an independent Octave session.
- Can be used as a context manager.
- Supports Unicode characters.
- Supports logging of session commands.
- Optional timeout command parameter to prevent runaway Octave sessions.

## Supported Python and dependency versions

This project follows [SPEC 0](https://scientific-python.org/specs/spec-0000/) for minimum supported Python and dependency versions.

## Installation

You must have GNU Octave installed and in your `PATH` environment variable.
Alternatively, you can set an `OCTAVE_EXECUTABLE` or `OCTAVE` environment
variable that points to `octave` executable itself.

You must have the Numpy and Scipy libraries for Python installed.
See the [installation instructions](https://blink1073.github.io/oct2py/source/installation.html) for more details.

Once the dependencies have been installed, run:

```bash
$ pip install oct2py
```

If using conda, it is available on conda-forge:

```bash
$ conda install -c conda-forge oct2py
```

## Documentation

Documentation is available [online](https://oct2py.readthedocs.io/en/latest/).

For version information, see the [Changelog](https://github.com/blink1073/oct2py/blob/main/CHANGELOG.md).

## JupyterHub with Qt Support

To enable Octave's Qt graphics toolkit in a JupyterHub environment (or any headless server), you need a virtual display. Install the required system packages:

```shell
apt-get install -y octave libglu1 xvfb texinfo fonts-freefont-otf ghostscript
```

Start `Xvfb` before launching JupyterHub (or in a server startup script):

```shell
Xvfb :99 -screen 0 1024x768x24 &
export DISPLAY=:99
```

Then configure oct2py to use the Qt backend in your notebook or script:

```python
from oct2py import octave
octave.eval("graphics_toolkit qt")
```

Alternatively, set `OCTAVE_EXECUTABLE` to run Octave under `xvfb-run`:

```shell
export OCTAVE_EXECUTABLE="xvfb-run octave"
```

For Binder-based deployments, the `binder/` directory in this repository contains an `apt.txt` listing required packages and a `start` script that launches `Xvfb` and exports `DISPLAY` before the Jupyter server starts, enabling Qt graphics out of the box.

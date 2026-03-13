# Installation

## Library Installation

You must have GNU Octave installed and in your PATH (see instructions
below). The library is only known to work with Octave 4.0+.
Additionally, you must have the Numpy and Scipy libraries for Python
installed. The simplest way to get them is to use the
[Anaconda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)
distribution.

Once the dependencies have been installed, run:

```bash
pip install oct2py
```

If using conda, it is available on conda-forge:

```bash
conda install -c conda-forge oct2py
```

## GNU Octave Installation

- On Linux platforms, try your package manager, or follow the
  instructions from
  [Octave](https://octave.org/doc/interpreter/Installation.html). You
  must also have gnuplot installed, and gnuplot-x11 or gnuplot-qt, if
  available.

- On OSX, the recommended methods are listed on this
  [wiki](https://wiki.octave.org/Octave_for_MacOS_X).

- On Windows, download the latest MinGW or .NET
  [version](https://sourceforge.net/projects/octave/files/Octave%20Windows%20binaries/).
  Cygwin is *NOT* supported. The MinGW version requires the
  [7zip](https://portableapps.com/apps/utilities/7-zip_portable) program
  for installation. Make sure to install gnuplot if prompted. Finally,
  to add Octave to your path. You can do so from the Environmental
  Variables dialog for your version of Windows, or set from the command
  prompt:

  ```
  setx PATH "%PATH%;<path-to-octave-dir>
  ```

  Where the folder `<path-to-octave-dir>` has the file `octave.exe`.
  If you see the message: "WARNINGS: The data being saved is truncated
  to 1024 characters" it means your PATH variable is too long. You'll
  have to manually trim it in the Windows Environmental Variables editor.

- To test, open a command window (or terminal) and type: `octave`. If
  Octave starts, you should be good to go.

- Alternatively, you can specify the path to your Octave executable by
  creating an `OCTAVE_EXECUTABLE` environmental variable. The default
  executable is `octave`.

## Graphics Backend (Qt vs gnuplot)

In some cases, the `qt` graphics toolkit is only available when running
with a display enabled.

On a remote system without a display, you can use `xvfb-run` to provide
a virtual framebuffer. For example:

```shell
export OCTAVE_EXECUTABLE="xvfb-run octave"
```

Or in the config file:

```python
c.OctaveMagics.executable = "xvfb-run octave"
```

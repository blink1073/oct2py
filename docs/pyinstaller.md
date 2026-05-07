# PyInstaller Support

Oct2py can be bundled into a standalone executable using
[PyInstaller](https://pyinstaller.org). The [`pyinstaller_test/`](https://github.com/blink1073/oct2py/tree/main/pyinstaller_test)
directory in the repository contains everything needed to verify this works.

## Files

| File | Purpose |
|------|---------|
| `pyinstaller_test/app.py` | Simple oct2py app that runs a set of Octave commands. This is the entry point that PyInstaller bundles. |
| `pyinstaller_test/oct2py_app.spec` | PyInstaller spec file. Uses `collect_all` for `oct2py` and `octave_kernel` to ensure all package data and dynamic imports are included. |
| `pyinstaller_test/test_build.py` | Standalone build-and-run script (not part of the pytest suite). Builds the executable, runs it, and asserts the expected output. |

## Running the test

Use the Justfile recipe (installs the `pyinstaller` dependency group automatically):

```bash
just pyinstaller-test
```

Or manually:

```bash
pip install pyinstaller
python pyinstaller_test/test_build.py
```

The script will:

1. Run PyInstaller using `oct2py_app.spec` and write the executable to `pyinstaller_test/dist/`.
1. Execute the resulting binary.
1. Assert that the output contains `"All Octave commands completed successfully."` — failing with a non-zero exit code if not.

## How the spec works

The spec uses PyInstaller's `collect_all` helper to gather every submodule,
data file, and hidden import from `oct2py` and `octave_kernel`:

```python
from PyInstaller.utils.hooks import collect_all

oct2py_datas, oct2py_binaries, oct2py_hiddenimports = collect_all("oct2py")
kernel_datas, kernel_binaries, kernel_hiddenimports = collect_all("octave_kernel")
```

Dependencies such as `scipy`, `tornado`, and `pyzmq` are handled by
PyInstaller's own built-in hooks and do not need to be listed manually.

## Notes

- GNU Octave must still be installed and on `PATH` on the machine that runs
  the bundled executable — oct2py launches Octave as a subprocess and does
  not bundle the Octave interpreter itself.

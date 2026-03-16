# Configuration & Settings

`Oct2PySettings` provides a single object that carries all session defaults.
It is built on [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/),
which means it reads values from environment variables automatically, so you
can configure oct2py without changing any code — useful in CI, Docker, or
shared environments.

## Quick start

```python
from oct2py import Oct2Py, Oct2PySettings

s = Oct2PySettings(backend="disable", timeout=30, plot_format="png")
oc = Oct2Py(settings=s)
```

Any field you do not set keeps its default value. Individual keyword
arguments to `Oct2Py` always take precedence over the settings object:

```python
# timeout from kwarg wins; everything else comes from settings
oc = Oct2Py(settings=s, timeout=5)
```

## Environment variables

Every field (except `executable`) is also readable from an environment
variable prefixed with `OCT2PY_`. This lets you configure a session
without modifying source code:

```shell
export OCT2PY_BACKEND=disable
export OCT2PY_TIMEOUT=60
export OCT2PY_PLOT_FORMAT=png
export OCT2PY_LOAD_OCTAVERC=false
python myscript.py          # default `octave` instance picks these up
```

The default global `octave` instance is created at import time, so env
vars must be set **before** `import oct2py`.

### Octave executable aliases

The `executable` field accepts two legacy environment variables in
addition to `OCT2PY_EXECUTABLE`:

| Variable | Priority |
|---|---|
| `OCTAVE_EXECUTABLE` | highest |
| `OCTAVE` | fallback |

```shell
export OCTAVE_EXECUTABLE=/opt/octave-9/bin/octave-cli
python myscript.py
```

## Reconfiguring the global instance

Use `oct2py.configure()` to replace the global `octave` instance with
one that uses new settings:

```python
import oct2py

oct2py.configure(backend="disable", timeout=60)
# oct2py.octave now uses those settings
```

You can also pass a pre-built `Oct2PySettings` object:

```python
from oct2py import Oct2PySettings
import oct2py

s = Oct2PySettings(backend="qt", plot_format="png", plot_width=1200)
oct2py.configure(settings=s)
```

## Common recipes

### Headless / CI environments

Suppress all figure rendering so that Octave never tries to open a
display:

```python
oc = Oct2Py(backend="disable")
```

Or via environment variable:

```shell
OCT2PY_BACKEND=disable python myscript.py
```

### Reproducible / sandboxed environments

Skip loading `~/.octaverc` to prevent user configuration from affecting
results:

```python
oc = Oct2Py(load_octaverc=False)
```

Or:

```shell
OCT2PY_LOAD_OCTAVERC=false python myscript.py
```

### Custom Octave executable

```python
oc = Oct2Py(executable="/opt/octave-9/bin/octave-cli")
```

After the session starts, `oc.executable` is updated to the full resolved
path actually used.

### Session-wide plot defaults

Set default format, size, and resolution so you do not have to repeat
them on every `eval` or `feval` call:

```python
oc = Oct2Py(plot_format="png", plot_width=1200, plot_height=900, plot_res=150)
oc.eval("plot([1 2 3])", plot_dir="/tmp/figs")   # uses the instance defaults
```

Per-call arguments still override the instance defaults:

```python
oc.eval("plot([1 2 3])", plot_dir="/tmp/figs", plot_format="svg")  # svg this time
```

### Passing extra CLI options

```python
oc = Oct2Py(extra_cli_options="--traditional")
```

### Settings from a `.env` file

`Oct2PySettings` is built on [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/),
which supports `.env` files out of the box:

```python
from oct2py import Oct2PySettings

s = Oct2PySettings(_env_file=".env")
oc = Oct2Py(settings=s)
```

The path is resolved relative to the current working directory. A `.env` file
might look like:

```ini
OCT2PY_BACKEND=disable
OCT2PY_TIMEOUT=120
OCT2PY_PLOT_FORMAT=png
```

## Settings reference

All fields and their defaults:

| Field | Default | `OCT2PY_` env var | Description |
|---|---|---|---|
| `executable` | `None` | `OCT2PY_EXECUTABLE` (also `OCTAVE_EXECUTABLE`, `OCTAVE`) | Path to Octave binary |
| `timeout` | `None` | `OCT2PY_TIMEOUT` | Command timeout in seconds |
| `oned_as` | `"row"` | `OCT2PY_ONED_AS` | Write 1-D arrays as `"row"` or `"column"` vectors |
| `temp_dir` | `None` | `OCT2PY_TEMP_DIR` | Directory for MAT exchange files |
| `convert_to_float` | `True` | `OCT2PY_CONVERT_TO_FLOAT` | Convert integers to float before sending to Octave |
| `backend` | `"default"` | `OCT2PY_BACKEND` | Graphics toolkit; `"disable"` suppresses all rendering |
| `keep_matlab_shapes` | `False` | `OCT2PY_KEEP_MATLAB_SHAPES` | Preserve MATLAB array shapes (scalars as `(1,1)` etc.) |
| `auto_show` | `None` | `OCT2PY_AUTO_SHOW` | Auto-display figures via matplotlib (default: on when `PYCHARM_HOSTED` is set) |
| `load_octaverc` | `True` | `OCT2PY_LOAD_OCTAVERC` | Source `~/.octaverc` on startup |
| `extra_cli_options` | `""` | `OCT2PY_EXTRA_CLI_OPTIONS` | Extra flags appended to the Octave invocation |
| `plot_format` | `"svg"` | `OCT2PY_PLOT_FORMAT` | Default saved-plot format |
| `plot_name` | `"plot"` | `OCT2PY_PLOT_NAME` | Default base name for saved plots |
| `plot_width` | `None` | `OCT2PY_PLOT_WIDTH` | Default plot width in pixels |
| `plot_height` | `None` | `OCT2PY_PLOT_HEIGHT` | Default plot height in pixels |
| `plot_res` | `None` | `OCT2PY_PLOT_RES` | Default plot resolution in DPI |

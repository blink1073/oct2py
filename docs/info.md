# Information

## Dynamic Functions

Oct2Py will create methods for you on the fly, which correspond to
Octave functions. For example:

```pycon
>>> from oct2py import octave
>>> octave.ones(3)
array([[1.,  1.,  1.],
   [1.,  1.,  1.],
   [1.,  1.,  1.]])
```

If you pass keyword arguments to the function, they will be treated as
Octave keywords, for example, `octave.plot(x, y, linewidth=3)` becomes
`plot(x, y, 'linewidth', 3)`. Arguments that are integer type will be
converted to floats unless you set `convert_to_float=False`.

Additionally, you can look up the documentation for one of these methods
using `help()`

```pycon
>>> from oct2py import octave
>>> help(octave.ones)  # doctest: +SKIP
'ones' is a built-in function
...
```

## Interactivity

Oct2Py supports code completion in IPython, so once you have created a
method, you can recall it on the fly, so `octave.one<TAB>` would give
you `ones`. Structs (mentioned below) also support code completion for
attributes.

You can share data with an Octave session explicitly using the `push`
and `pull` methods. When using other Oct2Py methods, the variable names
in Octave start with underscores because they are temporary (you would
only see this if you were using logging).

```pycon
>>> from oct2py import octave
>>> octave.push("a", 1)
>>> octave.pull("a")
1.0
```

## Workspace Access

The `workspace` attribute provides a dict-like interface to the Octave base
workspace, mirroring the `eng.workspace` API in MATLAB's Python engine:

```pycon
>>> from oct2py import octave
>>> octave.eval("x = 5", nout=0)
>>> octave.workspace["x"]
5.0
>>> octave.workspace["y"] = [1, 2, 3]
>>> octave.pull("y")
array([[1., 2., 3.]])
>>> del octave.workspace["y"]
```

This is equivalent to using `push` and `pull` directly, but can be more
natural when porting code from MATLAB's Python engine.

## Expression Pointers

Some Octave values — such as cell arrays of function handles — cannot be
converted to Python objects. Use `get_pointer` with `expr=True` to hold a
reference to such an expression and pass it directly to Octave functions
without a round-trip through Python:

```pycon
>>> from oct2py import octave
>>> ptr = octave.get_pointer('{@cos @sin}', expr=True)
>>> type(ptr).__name__
'OctaveVariablePtr'
>>> # Pass the cell of function handles to an Octave function unchanged
>>> octave.feval('cellfun', '@(f) f(0)', ptr)  # doctest: +SKIP
array([1., 0.])
```

`get_pointer(expr_str, expr=True)` assigns the expression to a uniquely
named temporary variable in the Octave workspace and returns a pointer to
it. The pointer's `address` is the internal variable name; the temporary
variable persists for the life of the session.

This is different from `get_pointer(name)` (without `expr=True`), which
looks up an *existing* named variable or function.

## Using M-Files

In order to use an m-file in Oct2Py you must first call `addpath` for
the directory containing the script. You can then use it as a dynamic
function or use the `eval` function to call it. Alternatively, you can
call `feval` with the full path.

```pycon
>>> from oct2py import octave
>>> octave.addpath("/path/to/")  # doctest: +SKIP
>>> octave.myscript(1, 2)  # doctest: +SKIP
>>> # or
>>> octave.eval("myscript(1, 2)")  # doctest: +SKIP
>>> # as feval
>>> octave.feval("/path/to/myscript", 1, 2)  # doctest: +SKIP
```

## Running Scripts and Accessing Their Variables

Octave scripts (as opposed to functions) assign variables directly into
the caller's workspace. When you call a script through the dynamic
dispatch mechanism (e.g. `octave.myscript()`), oct2py evaluates it
inside a temporary function scope, so any variables the script creates
are discarded when it returns and are not accessible via `pull`.

Use `Oct2Py.run()` instead. It executes the script in Octave's **base
workspace**, so variables it assigns persist and can be retrieved with
`pull`:

```pycon
>>> from oct2py import Oct2Py
>>> oc = Oct2Py()
>>> # myscript.m contains: result = [1, 2, 3];
>>> oc.run("/path/to/myscript.m")  # doctest: +SKIP
>>> oc.pull("result")              # doctest: +SKIP
array([1., 2., 3.])
```

`run` accepts the same optional keyword arguments as `eval` (`verbose`,
`timeout`, `stream_handler`, etc.).

> **Note:** This limitation does not apply to Octave *functions* — a
> function's return values are passed back to Python normally via
> `feval`. If you need to share data between Python and Octave in a
> flexible way, prefer writing a function that accepts arguments and
> returns results rather than relying on side-effects in the base
> workspace.

## Suppressing Output Capture

By default, `eval` and `feval` capture and return the Octave `ans` value.
Passing `quiet=True` executes the command but discards the result entirely,
returning `None`. This is useful in three situations:

- **Inspecting struct fields in Jupyter** — without `quiet=True`, the value is
  both printed by Octave and returned to the cell output, causing it to appear
  twice.
- **Non-serialisable types** — some Octave values (custom class objects, large
  sparse arrays, etc.) cannot be serialised to a MAT file. `quiet=True` lets
  you run the command for its side effects without triggering a serialisation
  error.
- **Fire-and-forget calls** — when you only care about the side effect (e.g.
  setting a variable, calling `disp`) and do not need the return value.

```pycon
>>> from oct2py import octave
>>> octave.push("s", {"field": [1, 2, 3]})
>>> result = octave.eval("s.field", quiet=True)  # prints once, returns None
>>> result is None
True
>>> result = octave.feval("max", [3, 1, 2], quiet=True)  # no return value
>>> result is None
True
```

## Direct Interaction

Oct2Py supports the Octave `keyboard` function which drops you into an
interactive Octave prompt in the current session. This also works in the
IPython Notebook. Note: If you use the `keyboard` command and the
session hangs, try opening an Octave session from your terminal and see
if the `keyboard` command hangs there too. You may need to update your
version of Octave.

## Logging

Oct2Py uses the standard Python `logging` module under the logger name
`"oct2py"`. Following Python library best practices, no handlers or levels
are configured by default — all log output is suppressed unless your
application sets up logging.

To see oct2py log output, configure the `"oct2py"` logger (or the root
logger) in your application:

```python
import logging

# Show INFO and above from oct2py
logging.getLogger("oct2py").setLevel(logging.INFO)
logging.getLogger("oct2py").addHandler(logging.StreamHandler())

# Or configure the root logger (affects all loggers):
logging.basicConfig(level=logging.INFO)
```

To enable DEBUG output (useful for troubleshooting), use `logging.DEBUG`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

When using pytest, pass `--log-cli-level=DEBUG` on the command line or add
to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
log_cli = true
log_cli_level = "DEBUG"
```

You can also pass a logger directly to the `Oct2Py` constructor or replace
it at any time:

```pycon
>>> import logging
>>> from oct2py import Oct2Py, get_log
>>> oc = Oct2Py(logger=get_log())
>>> oc.logger = get_log("new_log")
```

All Oct2Py methods support a `verbose` keyword. If True, the commands
are logged at the INFO level, otherwise they are logged at the DEBUG
level.

## Shadowed Function Names

If you'd like to call an Octave function that is also an Oct2Py method,
you must add a trailing underscore. For example:

```pycon
>>> from oct2py import octave
>>> octave.eval_("a=1")
1.0
```

The methods that shadow Octave builtins are: `exit` and `eval`.

## Timeout

Oct2Py sessions have a `timeout` attribute that determines how long to
wait for a command to complete. The default is 1e6 seconds (indefinite).
You may either set the timeout for the session, or as a keyword argument
to an individual command. The session is closed in the event of a
timeout.

```pycon
>>> from oct2py import octave
>>> octave.timeout = 3
>>> octave.sleep(2)  # doctest: +SKIP
>>> octave.sleep(2, timeout=1)  # doctest: +SKIP
Traceback (most recent call last):
...
oct2py.utils.Oct2PyError: Session timed out
```

## Configuration & Settings

All session defaults — timeout, executable, plot format, backend, and
more — can be set in one place using `Oct2PySettings` and read from
environment variables automatically. See the
[Configuration & Settings](settings.md) page for the full guide,
including env var names, `.env` file support, and common recipes for
headless, sandboxed, and CI environments.

```python
from oct2py import Oct2Py, Oct2PySettings

s = Oct2PySettings(backend="disable", timeout=30, plot_format="png")
oc = Oct2Py(settings=s)
```

Use `oct2py.configure()` to reconfigure the default global instance:

```python
import oct2py
oct2py.configure(backend="disable", timeout=60)
```

## Octave Executable

By default, oct2py uses `octave` as the Octave executable. To use a
different binary, pass it directly or set the `OCTAVE_EXECUTABLE`
environment variable:

```python
oc = Oct2Py(executable="/path/to/octave")
```

```shell
export OCTAVE_EXECUTABLE=/path/to/octave
```

When using IPython or Jupyter, you can also change it at runtime via the
`OctaveMagics` config trait without restarting the kernel:

```python
%config OctaveMagics.executable = "/path/to/octave"
```

## Graphics Toolkit

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

To inspect or change the active toolkit at runtime:

```pycon
>>> from oct2py import octave
>>> octave.available_graphics_toolkits()  # doctest: +SKIP
['qt', 'gnuplot']
>>> octave.graphics_toolkit("gnuplot")  # doctest: +SKIP
'gnuplot'
```

## PyCharm and IDE Integration

PyCharm's interactive console (and similar IDEs) displays matplotlib figures
inline but cannot capture Octave's native figure windows. As a result,
`octave.plot([1, 2, 3])` produces no visible output even though the figure
exists in Octave.

Oct2Py bridges this gap with two mechanisms:

**Automatic (`auto_show`):** When `PYCHARM_HOSTED` is set in the environment
(i.e. when running inside PyCharm), oct2py automatically renders open Octave
figures as PNG images and displays them via `matplotlib.pyplot.imshow()` after
every `eval` or `feval` call. No code changes are required — just install
matplotlib and run your plotting code as normal:

```pycon
>>> from oct2py import octave
>>> octave.plot([1, 2, 3])  # figure appears inline automatically in PyCharm
```

**Manual (`show()`):** In other environments, or to trigger display on demand,
call `show()` explicitly:

```pycon
>>> from oct2py import Oct2Py
>>> oc = Oct2Py()
>>> oc.plot([1, 2, 3])
>>> oc.show()  # renders and displays the figure via matplotlib
```

You can also enable or disable `auto_show` explicitly regardless of the
environment:

```pycon
>>> oc = Oct2Py(auto_show=True)   # always auto-display figures
>>> oc = Oct2Py(auto_show=False)  # never auto-display figures
```

`show()` requires `matplotlib` to be installed. If it is not available the
method returns silently, so it is safe to call unconditionally.

## Context Manager

Oct2Py can be used as a Context Manager. The session will be closed and
the temporary m-files will be deleted when the Context Manager exits.

```pycon
>>> from oct2py import Oct2Py
>>> with Oct2Py() as oc:  # doctest:+ELLIPSIS
...     oc.ones(10)
...
array([[1., 1., 1., 1., 1., 1., 1., 1., 1., 1.],
...
```

## Pandas

Oct2Py supports `pandas.Series` and `pandas.DataFrame` objects directly.
They are converted to their underlying NumPy array via `.values` before
being sent to Octave, so the Octave side always receives a plain numeric
array or matrix. The round-trip type is `ndarray`, not the original pandas
type.

```pycon
>>> import numpy as np
>>> import pandas as pd
>>> from oct2py import Oct2Py
>>> oc = Oct2Py()
>>> series = pd.Series([1.0, 2.0, 3.0])
>>> oc.push("s", series)
>>> oc.pull("s")
array([[1., 2., 3.]])
>>> data = np.array([[1.0, 2.0], [3.0, 4.0]])
>>> df = pd.DataFrame(data, columns=["a", "b"])
>>> oc.push("df", df)
>>> oc.pull("df")
array([[1., 2.],
       [3., 4.]])
>>> oc.exit()

```

## Structs

Struct is a convenience class that mimics an Octave structure variable
type. It is a dictionary with attribute lookup, and it creates
sub-structures on the fly of arbitrary nesting depth. It can be pickled.
You can also use tab completion for attributes when in IPython.

```pycon
>>> from oct2py import Struct
>>> test = Struct()
>>> test["foo"] = 1
>>> test.bizz["buzz"] = "bar"
>>> test
{'foo': 1, 'bizz': {'buzz': 'bar'}}
>>> import pickle
>>> p = pickle.dumps(test)
```

## Unicode

Oct2Py supports Unicode characters, so you may feel free to use m-files
that contain them.

## Speed

There is a performance penalty for passing information using MAT files.
If you have a lot of calculations, it is probably better to make an
m-file that does the looping and data aggregation, and pass that back to
Python for further processing. To see an example of the speed penalty on
your machine, run:

```pycon
>>> import oct2py
>>> oct2py.speed_check()  # doctest:+ELLIPSIS
Oct2Py speed test
...
```

## Threading

If you want to use threading, you *must* create a new `Oct2Py` instance
for each thread. The `octave` convenience instance is in itself *not*
threadsafe. Each `Oct2Py` instance has its own dedicated Octave session
and will not interfere with any other session.

## IPython Notebook

Oct2Py provides
[OctaveMagic](https://nbviewer.org/github/blink1073/oct2py/blob/main/example/octavemagic_extension.ipynb?create=1)
for IPython, including inline plotting in notebooks. This requires
IPython >= 1.0.0.

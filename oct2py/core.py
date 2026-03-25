"""Core oct2py functionality."""
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

import atexit
import contextlib
import glob
import logging
import os
import os.path as osp
import shutil
import signal
import sys
import tempfile
import threading
import uuid
import warnings
import weakref

import numpy as np
from metakernel.pexpect import EOF, TIMEOUT
from octave_kernel.kernel import STDIN_PROMPT, OctaveEngine

from .dynamic import (
    OctaveNamespaceProxy,
    OctavePtr,
    _make_function_ptr_instance,
    _make_namespace_proxy,
    _make_user_class,
    _make_variable_ptr_instance,
)
from .io import Cell, StructArray, read_file, write_file
from .settings import Oct2PySettings
from .utils import (
    Oct2PyError,
    Oct2PyWarning,
    _augment_path_for_windows,
    _create_macos_ramdisk,
    _detach_macos_ramdisk,
    get_log,
)

HERE = osp.realpath(osp.dirname(__file__))


# Registry of all live Oct2Py instances, held via weak references so they can
# be garbage-collected normally.  Used by the post-fork handler below.
_instances: weakref.WeakSet["Oct2Py"] = weakref.WeakSet()


def _reset_instances_after_fork() -> None:
    """Detach inherited Oct2Py sessions in a freshly forked child process.

    After os.fork() the child inherits a copy of every Oct2Py instance
    including its _engine (pexpect pty + Octave process PID).  Calling
    exit() or even letting __del__ run on these inherited engines is
    dangerous: terminate() sends SIGHUP to the Octave PID, which is the
    *parent's* live Octave process.  We neutralise all inherited sessions
    here so that neither exit() nor __del__ can harm the parent.
    """
    for inst in list(_instances):
        if inst._engine is not None:
            with contextlib.suppress(Exception):
                atexit.unregister(inst._engine._cleanup)
            with contextlib.suppress(Exception):
                # Mark the inherited pexpect spawn as already terminated so
                # that pexpect's __del__ skips waitpid().  Without this,
                # garbage-collecting the engine in the child would call
                # waitpid() on the parent's Octave PID, raising ECHILD.
                inst._engine.repl.terminated = True
        # Prevent exit() / __del__ from touching the parent's engine.
        inst._engine = None
        inst._temp_dir_owner = False
        inst._settings.temp_dir = None
    # The parent's atexit.register(shutil.rmtree, temp_dir, ...) calls are
    # inherited by the child.  Remove them so the child doesn't delete the
    # parent's /dev/shm temp directories on exit.  Any new Oct2Py instances
    # created in the child will register their own handlers afterwards.
    atexit.unregister(shutil.rmtree)


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset_instances_after_fork)


class OctaveWorkspaceProxy:
    """Dict-like proxy for the Octave base workspace.

    Allows MATLAB-style variable access::

        octave.workspace['x'] = 5
        octave.workspace['x']   # returns 5.0
        del octave.workspace['x']

    Parameters
    ----------
    session : Oct2Py
        The Oct2Py session to proxy.
    """

    _session: "Oct2Py"

    def __init__(self, session):
        self._session = session

    def __getitem__(self, name):
        """Return the named variable from the Octave workspace."""
        return self._session.pull(name)

    def __setitem__(self, name, value):
        """Set a variable in the Octave workspace."""
        self._session.push(name, value)

    def __delitem__(self, name):
        """Delete a variable from the Octave workspace."""
        exist = self._session._exist(name)
        if exist != 1:
            raise KeyError(name)
        self._session.eval('clear("%s")' % name, verbose=False)

    def __repr__(self):
        """Return a string representation of the proxy."""
        return f"OctaveWorkspaceProxy({self._session!r})"


class Oct2Py:
    """Manages an Octave session.

    Uses MAT files to pass data between Octave and Numpy.
    The function must either exist as an m-file in this directory or
    on Octave's path.
    The first command will take about 0.5s for Octave to load up.
    The subsequent commands will be much faster.

    You may provide a logger object for logging events, or the oct2py.get_log()
    default will be used.  When calling commands, logger.info() will be used
    to stream output, unless a `stream_handler` is provided.

    Parameters
    ----------
    settings : Oct2PySettings, optional
        Settings object supplying defaults for all other parameters.
        When omitted, a default ``Oct2PySettings()`` is created (which
        reads ``OCT2PY_*`` environment variables automatically).
        Explicit keyword arguments always override values from settings.
    logger : logging object, optional
        Optional logger to use for Oct2Py session
    timeout : float, optional
        Timeout in seconds for commands
    oned_as : {'row', 'column'}, optional
        If 'column', write 1-D numpy arrays as column vectors.
        If 'row', write 1-D numpy arrays as row vectors.}
    temp_dir : str, optional
        If specified, the session's MAT files will be created in the
        directory, otherwise a default directory is used.  On Linux,
        ``/dev/shm`` (a RAM-based tmpfs) is used automatically when
        available, which significantly reduces per-call overhead.  On
        other platforms you can point this at a tmpfs mount for the
        same benefit.
    convert_to_float : bool, optional
        If true, convert integer types to float when passing to Octave.
    backend: string, optional
        The graphics_toolkit to use for plotting.  Use ``"disable"`` to
        suppress all figure rendering (useful in headless or
        computation-only environments where a display is unavailable).
    keep_matlab_shapes: bool, optional
        If true, matlab shapes will be preserved (scalars as (1,1) etc)
    auto_show : bool, optional
        If True, automatically capture open Octave figures after each call
        and display them via matplotlib.  Defaults to True when the
        ``PYCHARM_HOSTED`` environment variable is set (i.e. when running
        inside PyCharm), False otherwise.  Set explicitly to override.
    extra_cli_options : str, optional
        Extra command-line options appended to the Octave invocation.
    executable : str, optional
        Path to the Octave executable. Resolved in order: this argument,
        ``OCTAVE_EXECUTABLE`` env var, ``octave``/``octave-cli`` on
        ``PATH``, then Flatpak.
    load_octaverc : bool, optional
        If True (default), source ``~/.octaverc`` during startup.  Set to
        False to skip loading the user init file, which is useful in
        reproducible or sandboxed environments where the init file may
        alter the path, set conflicting options, or is simply unavailable.
    plot_format : str, optional
        Default format for saved plots (default ``"svg"``).
    plot_name : str, optional
        Default base name for saved plots (default ``"plot"``).
    plot_width : int, optional
        Default plot width in pixels.
    plot_height : int, optional
        Default plot height in pixels.
    plot_res : int, optional
        Default plot resolution in pixels per inch.
    ramdisk_size_mb : int, optional
        macOS only.  When set to a positive integer, oct2py will create
        a temporary HFS+ RAM disk of the given size (in MiB) and use it
        as the MAT-file exchange directory.  The disk is unmounted
        automatically on session exit.  Has no effect on Linux (where
        ``/dev/shm`` is used automatically) or on Windows.  Defaults to
        ``0`` (disabled).
    """

    def __init__(  # noqa
        self,
        settings=None,
        logger=None,
        timeout=None,
        oned_as=None,
        temp_dir=None,
        convert_to_float=None,
        backend=None,
        keep_matlab_shapes=None,
        auto_show=None,
        extra_cli_options=None,
        executable=None,
        load_octaverc=None,
        plot_format=None,
        plot_name=None,
        plot_width=None,
        plot_height=None,
        plot_res=None,
        ramdisk_size_mb=None,
    ):
        if settings is None:
            settings = Oct2PySettings()
        # Apply any explicit kwargs as overrides on top of the settings object.
        _locals = locals()
        _overrides = {
            f: _locals[f]
            for f in Oct2PySettings.model_fields
            if f != "auto_show" and _locals.get(f) is not None
        }
        # Resolve auto_show: explicit kwarg > settings > env detection.
        _auto_show = auto_show if auto_show is not None else settings.auto_show
        if _auto_show is None:
            _auto_show = bool(os.environ.get("PYCHARM_HOSTED"))
            if _overrides.get("backend", settings.backend) == "disable":
                _auto_show = False
        self._settings = settings.model_copy(update={**_overrides, "auto_show": _auto_show})
        self._engine = None
        self._logger = None
        self.logger = logger
        self._temp_dir_owner = False
        self._ramdisk_device = None
        self._out_fh = None
        self._user_classes = {}
        self._function_ptrs = {}
        _instances.add(self)
        self.restart()

    @property
    def logger(self):
        """The logging instance used by the session."""
        return self._logger

    @logger.setter
    def logger(self, value):
        self._logger = value or get_log()
        if self._engine:
            self._engine.logger = self._logger

    @property
    def settings(self):
        """The session's current settings."""
        return self._settings

    @settings.setter
    def settings(self, value):
        self._settings = value

    def __enter__(self):
        """Return octave object, restart session if necessary"""
        if not self._engine:
            self.restart()
        return self

    def __exit__(self, type_, value, traceback):
        """Close session"""
        self.exit()

    def __del__(self):
        """Delete session"""
        try:  # noqa: SIM105
            self.exit()
        except Exception:  # noqa: S110  # pragma: no cover
            pass

    def exit(self):
        """Quits this octave session and cleans up."""
        if self._engine:
            if callable(atexit.unregister):
                atexit.unregister(self._engine._cleanup)
            self._engine.repl.terminate()
        self._engine = None
        if self._out_fh and not self._out_fh.closed:
            self._out_fh.close()
            self._out_fh = None
        if self._temp_dir_owner and self._settings.temp_dir and osp.isdir(self._settings.temp_dir):
            shutil.rmtree(self._settings.temp_dir, ignore_errors=True)
            self._settings.temp_dir = None
            self._temp_dir_owner = False
        if self._ramdisk_device:
            _detach_macos_ramdisk(self._ramdisk_device)
            self._ramdisk_device = None

    def push(self, name, var, timeout=None, verbose=True):
        """
        Put a variable or variables into the Octave session.

        Parameters
        ----------
        name : str or list
            Name of the variable(s).
        var : object or list
            The value(s) to pass.
        timeout : float
            Time to wait for response from Octave (per line).
        verbose: bool
             Log Octave output at INFO level.  If False, log at DEBUG level.

        Examples
        --------
        >>> from oct2py import octave
        >>> y = [1, 2]
        >>> octave.push('y', y)
        >>> octave.pull('y')
        array([[1., 2.]])
        >>> octave.push(['x', 'y'], ['spam', [1, 2, 3, 4]])
        >>> octave.pull(['x', 'y'])  # doctest: +SKIP
        [u'spam', array([[1, 2, 3, 4]])]

        Notes
        -----
        Integer type arguments will be converted to floating point
        unless `convert_to_float=False`.

        """
        timeout = timeout if timeout is not None else self._settings.timeout
        if isinstance(name, str):
            name = [name]
            var = [var]

        for n, v in zip(name, var, strict=False):
            self.feval("assignin", "base", n, v, nout=0, timeout=timeout, verbose=verbose)

    def pull(self, var, timeout=None, verbose=True):
        """
        Retrieve a value or values from the Octave session.

        Parameters
        ----------
        var : str or list
            Name of the variable(s) to retrieve.
        timeout : float, optional.
            Time to wait for response from Octave (per line).
        verbose: bool
             Log Octave output at INFO level.  If False, log at DEBUG level.

        Returns
        -------
        out : object
            Object returned by Octave.

        Raises
        ------
        Oct2PyError
            If the variable does not exist in the Octave session.

        Examples
        --------
          >>> from oct2py import octave
          >>> y = [1, 2]
          >>> octave.push('y', y)
          >>> octave.pull('y')
          array([[1., 2.]])
          >>> octave.push(['x', 'y'], ['spam', [1, 2, 3, 4]])
          >>> octave.pull(['x', 'y'])  # doctest: +SKIP
          [u'spam', array([[1, 2, 3, 4]])]

        """
        timeout = timeout if timeout is not None else self._settings.timeout
        if isinstance(var, str):
            var = [var]
        outputs = []
        for name in var:
            exist = self._exist(name)
            if exist == 1:
                outputs.append(self.feval("evalin", "base", name, timeout=timeout, verbose=verbose))
            else:
                outputs.append(self.get_pointer(name, timeout=timeout))

        if len(outputs) == 1:
            return outputs[0]
        return outputs

    def get_pointer(self, name, timeout=None, expr=False):
        """Get a pointer to a named object in the Octave workspace.

        Parameters
        ----------
        name: str
            The name of the object in the Octave workspace, or an Octave
            expression string when ``expr=True``.
        timeout: float, optional.
            Time to wait for response from Octave (per line).
        expr: bool, optional (default False)
            If True, treat `name` as an Octave expression string rather than a
            variable name. The expression is assigned to a unique temporary
            variable in the Octave workspace and a pointer to that variable is
            returned. Use this when you need to pass an expression that cannot
            be converted to a Python object (e.g. cell arrays of function
            handles like ``{@cos @sin}``).

            Note: the temporary variable persists in the Octave workspace for
            the lifetime of the session.

        Examples
        --------
        >>> from oct2py import octave
        >>> octave.eval('foo = [1, 2];')
        >>> ptr = octave.get_pointer('foo')
        >>> ptr.value
        array([[1., 2.]])
        >>> ptr.address
        'foo'
        >>> # Can be passed as an argument
        >>> octave.disp(ptr)  # doctest: +SKIP
        1  2

        >>> from oct2py import octave
        >>> sin = octave.get_pointer('sin')  # equivalent to `octave.sin`
        >>> sin.address
        '@sin'
        >>> x = octave.quad(sin, 0, octave.pi())
        >>> x
        2.0

        >>> from oct2py import octave
        >>> ptr = octave.get_pointer('{@cos @sin}', expr=True)
        >>> type(ptr).__name__
        'OctaveVariablePtr'
        >>> # Pass the cell of function handles to an Octave function
        >>> octave.feval('cellfun', '@(f) f(0)', ptr)  # doctest: +SKIP

        Notes
        -----
        Pointers can be passed to `feval` or dynamic functions as function
        arguments.  A pointer passed as a nested value will be passed by value
        instead.

        Raises
        ------
        Oct2PyError
            If the variable does not exist in the Octave session or is of
            unknown type.

        Returns
        -------
        A variable, object, user class, or function pointer as appropriate.
        """
        timeout = timeout if timeout is not None else self._settings.timeout
        if expr:
            tmp_name = f"_oct2py_expr_{uuid.uuid4().hex}"
            self.eval(f"{tmp_name} = {name}", timeout=timeout)
            return _make_variable_ptr_instance(self, tmp_name)

        exist = self._exist(name)
        isobject = self._isobject(name, exist)

        if exist == 0:
            raise Oct2PyError('"%s" is undefined' % name)

        elif exist == 1:
            return _make_variable_ptr_instance(self, name)

        elif isobject:
            return self._get_user_class(name)

        elif exist in [2, 3, 5]:
            return self._get_function_ptr(name)

        raise Oct2PyError('Unknown type for object "%s"' % name)

    def extract_figures(self, plot_dir, remove=False):
        """Extract the figures in the directory to IPython display objects.

        Parameters
        ----------
        plot_dir: str
            The plot dir where the figures were created.
        remove: bool, optional.
            Whether to remove the plot directory after saving.

        Returns
        -------
        The list of figure objects.
        """
        if not self._engine:
            msg = "Session is not open"
            raise Oct2PyError(msg)
        figures = self._engine.extract_figures(plot_dir, remove)
        return figures

    def show(self):
        """Render open Octave figures and display them using matplotlib.

        Captures all currently open Octave figure windows as PNG images and
        displays them via :func:`matplotlib.pyplot.imshow`.  This is useful
        in environments such as PyCharm that can display matplotlib figures
        inline but cannot show Octave's native figure windows.

        Requires ``matplotlib`` to be installed.  If it is not available,
        the method returns silently.

        This is called automatically after each eval/feval when
        ``auto_show=True`` (which is the default inside PyCharm).

        Examples
        --------
        >>> import oct2py  # doctest: +SKIP
        >>> oc = oct2py.Oct2Py()  # doctest: +SKIP
        >>> _ = oc.plot([1, 2, 3])  # doctest: +SKIP
        >>> oc.show()  # displays the Octave figure inline  # doctest: +SKIP
        """
        self._show_figures()

    def _show_figures(self):
        """Capture open Octave figures and display them via matplotlib."""
        if not self._engine:
            return
        if self._settings.backend == "disable":
            return
        try:
            import matplotlib.image as mpimg  # noqa: PLC0415
            import matplotlib.pyplot as plt  # noqa: PLC0415
        except ImportError:  # pragma: no cover
            return

        plot_dir = tempfile.mkdtemp(dir=self._settings.temp_dir)
        try:
            # Temporarily switch to inline mode so _make_figures uses a
            # headless-compatible toolkit (gnuplot/qt offscreen) rather than
            # the default interactive toolkit, which requires a display.
            saved = self._engine.plot_settings.copy()
            self._engine.plot_settings = {**saved, "backend": "inline"}
            try:
                self._engine.make_figures(plot_dir)
            finally:
                self._engine.plot_settings = saved

            figure_files = sorted(glob.glob(osp.join(plot_dir, "*")))
            for img_path in figure_files:
                img = mpimg.imread(img_path)
                _, ax = plt.subplots()
                ax.imshow(img)
                ax.axis("off")
            if figure_files:
                plt.show()
        finally:
            shutil.rmtree(plot_dir, ignore_errors=True)

    def feval(self, func_path, *func_args, **kwargs):
        """Run a function in Octave and return the result.

        Parameters
        ----------
        func_path : str
            Name of function to run or a path to an m-file.
        func_args : object, optional
            Args to send to the function.

        Other Parameters
        ----------------
        nout : int or str, optional
            The desired number of returned values, defaults to 1. If nout
            value is 'max_nout', _get_max_nout() will be used.
        quiet : bool, optional
            If True, execute the function but do not capture or return any
            output.  Takes precedence over ``nout``.
        store_as : str, optional
            If given, saves the result to the given Octave variable name
            instead of returning it.
        verbose : bool, optional
            Log Octave output at INFO level.  If False, log at DEBUG level.
        stream_handler : callable, optional
            A function that is called for each line of output from the
            evaluation.
        timeout : float, optional
            The timeout in seconds for the call.
        plot_dir : str, optional
            If specified, save the session's plot figures to the plot
            directory instead of displaying the plot window.
        plot_backend : str, optional
            The plotting back end to use.
        plot_name : str, optional
            Saved plots will start with `plot_name` and
            end with "_%%.xxx' where %% is the plot number and
            xxx is the `plot_format`.
        plot_format : str, optional
            The format in which to save the plot.
        plot_width : int, optional
            The plot width in pixels.
        plot_height : int, optional
            The plot height in pixels.

        Notes
        -----
        The function arguments passed follow Octave calling convention, not
        Python. That is, all values must be passed as a comma separated list,
        not using `x=foo` assignment.

        **Plot rendering limitation (issue #172):** oct2py executes Octave
        synchronously, so figure updates triggered by ``pause()`` calls inside
        a ``.m`` function are not rendered mid-execution — plots are only
        exposed after the entire function returns.  For interactive display
        this means figures appear at the end of the call, not incrementally.
        To capture figures from inside a ``.m`` file programmatically, pass
        ``plot_dir`` and then call :meth:`extract_figures`::

            plot_dir = tempfile.mkdtemp()
            octave.feval("my_func.m", plot_dir=plot_dir)
            imgs = octave.extract_figures(plot_dir)

        Examples
        --------
        >>> from oct2py import octave
        >>> cell = octave.feval('cell', 10, 10, 10)
        >>> cell.shape
        (10, 10, 10)

        >>> from oct2py import octave
        >>> x = octave.feval('linspace', 0, octave.pi() / 2)
        >>> x.shape
        (1, 100)

        >>> from oct2py import octave
        >>> x = octave.feval('svd', octave.hilb(3))
        >>> x
        array([[1.40831893],
               [0.12232707],
               [0.00268734]])
        >>> # specify three return values
        >>> (u, v, d) = octave.feval('svd', octave.hilb(3), nout=3)
        >>> u.shape
        (3, 3)

        Returns
        -------
        The Python value(s) returned by the Octave function call.
        """  # noqa: DOC102, DOC103
        if not self._engine:
            msg = "Session is not open"
            raise Oct2PyError(msg)

        # nout handler
        nout = kwargs.get("nout")
        if kwargs.get("quiet"):
            nout = -1
        elif nout is None:
            nout = 1
        elif nout == "max_nout":
            nout = self._get_max_nout(func_path)

        plot_dir = kwargs.get("plot_dir")

        # Choose appropriate plot backend.
        default_backend = "inline" if plot_dir else self._settings.backend
        backend = kwargs.get("plot_backend", default_backend)
        # Map "disable" to "inline" so octave_kernel sets defaultfigurevisible=off.
        if backend == "disable":
            backend = "inline"

        settings = dict(
            backend=backend,
            format=kwargs.get("plot_format"),
            name=kwargs.get("plot_name"),
            width=kwargs.get("plot_width"),
            height=kwargs.get("plot_height"),
            resolution=kwargs.get("plot_res"),
        )
        self._engine.plot_settings = settings

        _is_dotted_name = kwargs.pop("_is_dotted_name", False)
        if _is_dotted_name:
            func_name = func_path
            dname = ""
        else:
            dname = osp.dirname(func_path)
            fname = osp.basename(func_path)
            func_name, ext = osp.splitext(fname)
            if ext and ext != ".m":
                msg = "Need to give path to .m file"
                raise TypeError(msg)

        if func_name == "clear":
            msg = 'Cannot use `clear` command directly, use eval("clear(var1, var2)")'
            raise Oct2PyError(msg)

        stream_handler = kwargs.get("stream_handler")
        verbose = kwargs.get("verbose", True)
        store_as = kwargs.get("store_as", "")
        _t = kwargs.get("timeout")
        timeout = _t if _t is not None else self._settings.timeout
        if not stream_handler:
            stream_handler = self.logger.info if verbose else self.logger.debug

        return self._feval(
            func_name,
            func_args,
            dname=dname,
            nout=nout,
            timeout=timeout,
            stream_handler=stream_handler,
            store_as=store_as,
            plot_dir=plot_dir,
        )

    def eval(  # noqa: PLR0913
        self,
        cmds,
        verbose=True,
        timeout=None,
        stream_handler=None,
        temp_dir=None,
        plot_dir=None,
        plot_name=None,
        plot_format=None,
        plot_backend=None,
        plot_width=None,
        plot_height=None,
        plot_res=None,
        nout=0,
        quiet=False,
        **kwargs,
    ):
        """Evaluate an Octave command or commands.

        Parameters
        ----------
        cmds : str or list
            Commands(s) to pass to Octave.
        verbose : bool, optional
             Log Octave output at INFO level.  If False, log at DEBUG level.
        stream_handler: callable, optional
            A function that is called for each line of output from the
            evaluation.
        timeout : float, optional
            Time to wait for response from Octave (per line).  If not given,
            the instance `timeout` is used.
        nout : int or str, optional.
            The desired number of returned values, defaults to 0.  If nout
            is 0, the `ans` will be returned as the return value. If nout
            value is 'max_nout', _get_max_nout() will be used.
        quiet : bool, optional
            If True, execute the command(s) but do not capture or return any
            output.  Useful when ``ans`` is not serialisable, or to avoid
            double-printing in Jupyter.  Takes precedence over ``nout``.
        temp_dir: str, optional
            If specified, the session's MAT files will be created in the
            directory, otherwise a the instance `temp_dir` is used.
            a shared memory (tmpfs) path.
        plot_dir: str, optional
            If specified, save the session's plot figures to the plot
            directory instead of displaying the plot window.
        plot_name : str, optional
            Saved plots will start with `plot_name` and
            end with "_%%.xxx' where %% is the plot number and
            xxx is the `plot_format`.
        plot_format: str, optional
            The format in which to save the plot (PNG by default).
        plot_width: int, optional
            The plot with in pixels.
        plot_height: int, optional
            The plot height in pixels.
        plot_backend: str, optional
            The plot backend to use.
        plot_res: int, optional
            The plot resolution in pixels per inch.
        **kwargs Deprecated kwargs.

        Examples
        --------
        >>> from oct2py import octave
        >>> octave.eval('disp("hello")') # doctest: +SKIP
        hello
        >>> x = octave.eval('round(quad(@sin, 0, pi/2));')
        >>> x
        1.0

        >>> a = octave.eval('disp("hello");1;')  # doctest: +SKIP
        hello
        >>> a = octave.eval('disp("hello");1;', verbose=False)
        >>> a
        1.0

        >>> from oct2py import octave
        >>> lines = []
        >>> octave.eval('for i = 1:3; disp(i);end', \
                        stream_handler=lines.append)
        >>> lines  # doctest: +SKIP
        [' 1', ' 2', ' 3']

        Returns
        -------
        out : object
            Octave "ans" variable, or None.

        Notes
        -----
        The deprecated `log` kwarg will temporarily set the `logger` level to
        `WARN`.  Using the `logger` settings directly is preferred.
        The deprecated `return_both` kwarg will still work, but the preferred
        method is to use the `stream_handler`.  If `stream_handler` is given,
        the `return_both` kwarg will be honored but will give an empty string
        as the response.

        Raises
        ------
        Oct2PyError
            If the command(s) fail.
        """  # noqa: DOC103
        if isinstance(cmds, str):
            cmds = [cmds]

        timeout = timeout if timeout is not None else self._settings.timeout
        plot_name = plot_name if plot_name is not None else self._settings.plot_name
        plot_format = plot_format if plot_format is not None else self._settings.plot_format
        plot_width = plot_width if plot_width is not None else self._settings.plot_width
        plot_height = plot_height if plot_height is not None else self._settings.plot_height
        plot_res = plot_res if plot_res is not None else self._settings.plot_res

        prev_temp_dir = self._settings.temp_dir
        self._settings.temp_dir = temp_dir or self._settings.temp_dir
        prev_log_level = self.logger.level

        if kwargs.get("log") is False:
            self.logger.setLevel(logging.WARN)

        for name in ["log", "return_both"]:
            if name not in kwargs:
                continue
            msg = "Using deprecated `%s` kwarg, see docs on `Oct2Py.eval()`"
            warnings.warn(msg % name, Oct2PyWarning, stacklevel=2)

        return_both = kwargs.pop("return_both", False)
        lines: list[str] = []
        if return_both and not stream_handler:
            stream_handler = lines.append

        ans = None
        for cmd in cmds:
            resp = self.feval(
                "evalin",
                "base",
                cmd,
                nout=nout,
                quiet=quiet,
                timeout=timeout,
                stream_handler=stream_handler,
                verbose=verbose,
                plot_dir=plot_dir,
                plot_name=plot_name,
                plot_format=plot_format,
                plot_backend=plot_backend,
                plot_width=plot_width,
                plot_height=plot_height,
                plot_res=plot_res,
            )
            if resp is not None:
                ans = resp

        self._settings.temp_dir = prev_temp_dir
        self.logger.setLevel(prev_log_level)

        if return_both:
            return "\n".join(lines), ans
        return ans

    def run(self, script, **kwargs):
        """Run an Octave script file in the base workspace.

        Unlike calling ``octave.run(script)`` via dynamic dispatch (which runs
        the script inside a temporary function scope and discards any variables
        it creates), this method executes the script through ``evalin('base',
        ...)``, so variables assigned by the script persist in the Octave base
        workspace and can be retrieved with :meth:`pull`.

        Parameters
        ----------
        script : str
            Name of the script or path to an ``.m`` file, passed directly to
            Octave's ``run()`` built-in.
        **kwargs
            Additional keyword arguments forwarded to :meth:`eval` (e.g.
            ``verbose``, ``timeout``, ``stream_handler``).

        Examples
        --------
        >>> import os, tempfile
        >>> from oct2py import Oct2Py
        >>> oc = Oct2Py()
        >>> with tempfile.NamedTemporaryFile(suffix='.m', mode='w', delete=False) as f:
        ...     _ = f.write('b = 42;')
        ...     script_path = f.name
        >>> oc.run(script_path)
        >>> oc.pull('b')
        42.0
        >>> oc.exit()
        >>> os.unlink(script_path)
        """
        # Escape backslashes and single quotes so the path is safe inside
        # an Octave single-quoted string literal.
        safe = script.replace("\\", "/").replace("'", "''")
        kwargs.setdefault("nout", 0)
        self.eval(f"run('{safe}')", **kwargs)

    @property
    def workspace(self):
        """A dict-like proxy for the Octave base workspace.

        Supports MATLAB-style variable access::

            octave.workspace['x'] = 5
            octave.workspace['x']   # returns 5.0
            del octave.workspace['x']

        Returns
        -------
        OctaveWorkspaceProxy
        """
        return OctaveWorkspaceProxy(self)

    def restart(self):
        """Restart an Octave session in a clean state"""
        if self._engine:
            self._engine.repl.terminate()

        # Use the stored executable (may be empty, letting OctaveEngine resolve).
        _executable = self._settings.executable or ""

        # Preserve the SIGINT handler across engine startup.  The underlying
        # pexpect spawn temporarily replaces SIGINT with SIG_DFL so that the
        # Octave child process inherits a clean disposition.  If a concurrent
        # thread (e.g. from a scipy/sympy lazy initialiser) transiently sets
        # SIGINT to SIG_IGN at exactly the wrong moment, pexpect's finally
        # block can "restore" that transient SIG_IGN value, leaving SIGINT
        # permanently ignored for the rest of the Python process (issue #168).
        # Restoring the handler we observed before the spawn prevents engine
        # startup from having any net effect on the caller's SIGINT disposition.
        _saved_sigint = None
        if threading.current_thread() is threading.main_thread():
            with contextlib.suppress(Exception):
                _saved_sigint = signal.getsignal(signal.SIGINT)

        _qt_plugin_path = None
        try:
            # Use a weakref-based wrapper so that OctaveEngine (and its atexit
            # registration) does not hold a strong reference back to this Oct2Py
            # instance, which would otherwise prevent __del__ / exit() from ever
            # being called and cause Octave subprocesses to accumulate.
            #
            # Strip QT_QPA_PLATFORM_PLUGIN_PATH before spawning Octave if it
            # was injected by opencv-python.  opencv injects its own bundled
            # Qt plugin directory (always under a "cv2" package path) into
            # this variable; pexpect inherits os.environ, so the Octave child
            # process would pick up the incompatible path and crash with
            # "Could not load the Qt platform plugin" (issue #240).
            # System-set paths (e.g. from the octave_kernel CI action on
            # macOS) are safe to keep — stripping them breaks octave_kernel's
            # _validate_executable, which needs to run octave successfully.
            _qt_path = os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH", "")
            _qt_plugin_path = (
                os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH") if "cv2" in _qt_path else None
            )
            _weak_self = weakref.ref(self)

            def _stdin_handler(line):
                inst = _weak_self()
                if inst is not None:
                    return inst._handle_stdin(line)
                return None

            self._engine = OctaveEngine(
                executable=_executable,
                stdin_handler=_stdin_handler,
                logger=self.logger,
                cli_options=self._settings.extra_cli_options,
                load_octaverc=self._settings.load_octaverc,
            )
        except Exception as e:
            raise Oct2PyError(str(e)) from None
        finally:
            if _saved_sigint is not None:
                with contextlib.suppress(Exception):
                    signal.signal(signal.SIGINT, _saved_sigint)
            if _qt_plugin_path is not None:
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = _qt_plugin_path

        self._settings.executable = self._engine.executable
        _augment_path_for_windows(self._settings.executable)

        # Set up the temp directory for MAT file exchange.
        if self._settings.temp_dir is None:
            # Prefer a RAM-based filesystem (tmpfs) for faster file I/O.
            # On Linux, /dev/shm is always in RAM and avoids disk latency,
            # which is critical for performance in Octave 7+ where save/load
            # can be significantly slower on disk-backed filesystems.
            executable = self._engine.executable
            sandboxed = "snap" in executable or "flatpak" in executable
            shm = "/dev/shm"  # noqa: S108
            if not sandboxed and osp.isdir(shm) and os.access(shm, os.W_OK):
                self._settings.temp_dir = tempfile.mkdtemp(dir=shm, prefix="oct2py_")
                atexit.register(shutil.rmtree, self._settings.temp_dir, True)
            elif sys.platform == "darwin" and not sandboxed and self._settings.ramdisk_size_mb > 0:
                device, mount = _create_macos_ramdisk(self._settings.ramdisk_size_mb)
                if device:
                    self._ramdisk_device = device
                    self._settings.temp_dir = tempfile.mkdtemp(dir=mount, prefix="oct2py_")
                    atexit.register(shutil.rmtree, self._settings.temp_dir, True)
                    atexit.register(_detach_macos_ramdisk, device)
            if self._settings.temp_dir is None:
                self._settings.temp_dir = os.path.join(self._engine.tmp_dir, "oct2py")
                os.makedirs(self._settings.temp_dir, exist_ok=True)
            self._temp_dir_owner = True

        # Pre-open writer.mat so the file descriptor is reused across calls,
        # avoiding repeated open/close syscall overhead.
        if self._out_fh is None or self._out_fh.closed:
            self._out_fh = open(osp.join(self._settings.temp_dir, "writer.mat"), "w+b")  # noqa: SIM115

        # Add local Octave scripts.
        self._engine.eval('addpath("%s");' % HERE.replace(osp.sep, "/"))

        # Octave's default max_recursion_depth is 256, which is lower than
        # MATLAB's default and causes deep recursive functions to crash the
        # session.  Raise it to match a more permissive default (issue #326).
        self._engine.eval("max_recursion_depth(2500);")

    def _feval(  # noqa
        self,
        func_name,
        func_args=(),
        dname="",
        nout=0,
        timeout=None,
        stream_handler=None,
        store_as="",
        plot_dir=None,
    ):
        """Run the given function with the given args."""
        engine = self._engine
        if engine is None:
            msg = "Session is closed"
            raise Oct2PyError(msg)

        # Set up our mat file paths.
        out_file = osp.join(self._settings.temp_dir, "writer.mat")
        out_file = out_file.replace(osp.sep, "/")
        in_file = osp.join(self._settings.temp_dir, "reader.mat")
        in_file = in_file.replace(osp.sep, "/")

        func_args = list(func_args)
        ref_indices = []
        for i, value in enumerate(func_args):
            if isinstance(value, OctavePtr):
                ref_indices.append(i + 1)
                func_args[i] = value.address
        ref_arr = np.array(ref_indices)

        # Save the request data to the output file.
        req = dict(
            func_name=func_name,
            func_args=tuple(func_args),
            dname=dname or "",
            nout=nout,
            store_as=store_as or "",
            ref_indices=ref_arr,
        )

        write_file(
            req,
            self._out_fh,
            oned_as=self._settings.oned_as,
            convert_to_float=self._settings.convert_to_float,
        )

        # Set up the engine and evaluate the `_pyeval()` function.
        engine.line_handler = stream_handler or self.logger.info
        if timeout is None:
            timeout = self._settings.timeout

        try:
            engine.eval(f'_pyeval("{out_file}", "{in_file}");', timeout=timeout)
        except KeyboardInterrupt:
            stream_handler(engine.repl.interrupt())
            raise
        except TIMEOUT:
            stream_handler(engine.repl.interrupt())
            msg = "Timed out, interrupting"
            raise Oct2PyError(msg) from None
        except EOF:
            if not self._engine:
                return
            stream_handler(engine.repl.child.before)
            self.restart()
            msg = "Session died, restarting"
            raise Oct2PyError(msg) from None

        # Read in the output.
        resp = read_file(in_file, self)
        if resp["err"]:
            msg = self._parse_error(resp["err"])
            raise Oct2PyError(msg)

        result = resp["result"].ravel().tolist()
        if isinstance(result, list) and len(result) == 1:
            result = result[0]

        # Check for sentinel value.
        if (
            isinstance(result, Cell)
            and result.size == 1
            and isinstance(result[0], str)
            and result[0] == "__no_value__"
        ):
            result = None

        if plot_dir:
            engine.make_figures(plot_dir)
        elif self._settings.auto_show:
            self._show_figures()

        return result

    def _parse_error(self, err):
        """Create a traceback for an Octave evaluation error."""
        self.logger.debug(err)
        stack = err.get("stack", [])
        if not err["message"].startswith("parse error:"):
            err["message"] = "error: " + err["message"]
        errmsg = "Octave evaluation error:\n%s" % err["message"]

        if not isinstance(stack, StructArray):
            return errmsg

        errmsg += "\nerror: called from:"
        for item in stack[:-1]:
            errmsg += "\n    %(name)s at line %(line)d" % item
            try:  # noqa
                errmsg += ", column %(column)d" % item
            except Exception:  # noqa
                pass
        return errmsg

    def _handle_stdin(self, line):
        """Handle a stdin request from the session."""
        return input(line.replace(STDIN_PROMPT, ""))

    def _print_doc(self, name):
        """
        Print the documentation of an Octave procedure or object.

        Parameters
        ----------
        name : str
            Function name to search for.
        """
        print(self._get_doc(name))  # noqa

    def _get_doc(self, name):
        """
        Get the documentation of an Octave procedure or object.

        Parameters
        ----------
        name : str
            Function name to search for.

        Returns
        -------
        out : str
          Documentation string.

        Raises
        ------
        Oct2PyError
           If the procedure or object function has a syntax error.

        """
        doc = "No documentation for %s" % name

        engine = self._engine
        if not engine:
            msg = "Session is not open"
            raise Oct2PyError(msg)
        doc = engine.eval('help("%s")' % name, silent=True)

        if "syntax error:" in doc.lower():
            raise Oct2PyError(doc)

        if "error:" in doc.lower():
            doc = engine.eval('type("%s")' % name, silent=True)
            doc = "\n".join(doc.splitlines()[:3])

        default = self.feval.__doc__
        default = (
            "        " + default[default.find("func_args:") :]  # type:ignore[index,union-attr]
        )
        default = "\n".join([line[8:] for line in default.splitlines()])

        doc = "\n".join(doc.splitlines())
        doc = "\n" + doc + "\n\nParameters\n----------\n" + default
        doc += "\n**kwargs - Deprecated keyword arguments\n\n"
        doc += "Notes\n-----\n"
        doc += "Keyword arguments to dynamic functions are deprecated.\n"
        doc += "The `plot_*` kwargs will be ignored, but the rest will\n"
        doc += "used as key - value pairs as in version 3.x.\n"
        doc += "Pass `plot_dir` to `feval` or `eval` for inline plot capture,\n"
        doc += "and use `func_args` directly for key - value pairs."
        return doc

    def _exist(self, name):
        """Test whether a name exists and return the name code.

        Raises an error when the name does not exist.
        """
        cmd = 'exist("%s")' % name
        if not self._engine:
            msg = "Session is not open"
            raise Oct2PyError(msg)
        resp = self._engine.eval(cmd, silent=True).strip()
        exist = int(resp.split()[-1])
        if exist == 0:
            cmd = "class(%s)" % name
            resp = self._engine.eval(cmd, silent=True).strip()
            if "error:" not in resp:
                exist = 2
        return exist

    def _isobject(self, name, exist):
        """Test whether the name is an object."""
        if exist in [2, 5]:
            return False
        cmd = "isobject(%s)" % name
        if not self._engine:
            msg = "Session is not open"
            raise Oct2PyError(msg)
        resp = self._engine.eval(cmd, silent=True).strip()
        return resp == "ans =  1"

    def _get_function_ptr(self, name):
        """Get or create a function pointer of the given name."""
        func = _make_function_ptr_instance
        self._function_ptrs.setdefault(name, func(self, name))
        return self._function_ptrs[name]

    def _get_user_class(self, name, attrs=None):
        """Get or create a user class of the given type."""
        if name not in self._user_classes:
            self._user_classes[name] = _make_user_class(self, name, attrs=attrs)
        return self._user_classes[name]

    def __getattr__(self, attr):
        """Automatically creates a wrapper to an Octave function or object.

        Adapted from the mlabwrap project.
        """
        # needed for help(Oct2Py())
        if attr.startswith("__"):
            return super().__getattr__(attr)  # type:ignore[misc]

        # close_ -> close
        name = attr[:-1] if attr[-1] == "_" else attr

        if self._engine is None:
            msg = "Session is closed"
            raise Oct2PyError(msg)

        # Make sure the name exists.
        exist = self._exist(name)

        if exist not in [2, 3, 5, 103]:
            if exist in (0, 7):
                # Name not found or is a directory — may be an Octave package
                # namespace (+package). Return a lazy proxy; Octave will report
                # an error at call time if the name is truly invalid.
                return _make_namespace_proxy(self, name)
            msg = 'Name "%s" is not a valid callable, use `pull` for variables'
            raise Oct2PyError(msg % name)

        if name == "clear":
            msg = 'Cannot use `clear` command directly, use `eval("clear(var1, var2)")`'
            raise Oct2PyError(msg)

        # Check for user defined class.
        if self._isobject(name, exist):
            obj = self._get_user_class(name)
        else:
            obj = self._get_function_ptr(name)

        # !!! attr, *not* name, because we might have python keyword name!
        # Don't cache namespace proxies — the namespace isn't resolved yet.
        if not isinstance(obj, OctaveNamespaceProxy):
            setattr(self, attr, obj)

        return obj

    def _get_max_nout(self, func_path):
        """Get or count maximum nout of .m function."""

        if not osp.isabs(func_path):
            func_path = self.which(func_path)

        nout = 0  # default nout of eval
        status = "NOT FUNCTION"
        if func_path.endswith(".m"):  # only if `func_path` is .m file
            with open(func_path, encoding="utf8") as fid:
                for line in fid:
                    if line[0] != "f":  # noqa # not function
                        if status == "NOT FUNCTION":
                            continue
                    line = line.translate(  # noqa
                        str.maketrans("", "", "[]()")
                    ).split()  # type:ignore[assignment]
                    try:  # noqa
                        line.remove("function")  # type:ignore[attr-defined]
                    except Exception:  # noqa
                        pass
                    for char in line:
                        if char == "...":
                            status = "FUNCTION"
                            continue
                        if char != "=":
                            nout += 1
                        else:
                            return nout

        return nout

import gc
import glob
import logging
import os
import shutil
import signal
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO

import numpy as np
import pandas as pd
import pytest

import oct2py
from oct2py import Oct2Py, Oct2PyError, StructArray


def _multiprocessing_worker(_):
    """Top-level worker so it is picklable by multiprocessing.Pool."""
    oc = Oct2Py()
    result = oc.sum([1, 2, 3])
    oc.exit()
    return float(result)


def _multiprocessing_worker_exit(_):
    """Worker that explicitly exits inherited Oct2Py sessions to trigger the bug."""
    import oct2py as _oct2py

    # Explicitly calling exit() on the inherited global in the child kills the
    # parent's Octave process via os.kill(pid, signal).  This is the bug.
    _oct2py.octave.exit()
    oc = Oct2Py()
    result = oc.sum([1, 2, 3])
    oc.exit()
    return float(result)


class TestMisc:
    oc: Oct2Py
    _flatpak: bool

    @classmethod
    def setup_class(cls):
        cls.oc = Oct2Py()
        # Flatpak sandboxes Octave so it cannot access arbitrary host paths.
        cls._flatpak = cls.oc._engine.executable.startswith("flatpak")
        tests_dir = os.path.dirname(__file__)
        if cls._flatpak:
            # Copy all .m files and Octave class directories (@Foo/) into the
            # sandbox-accessible temp_dir and add that to the path instead.
            for item in os.listdir(tests_dir):
                src = os.path.join(tests_dir, item)
                if os.path.isfile(src) and item.endswith(".m"):
                    shutil.copy2(src, cls.oc.temp_dir)
                elif os.path.isdir(src) and item.startswith("@"):
                    shutil.copytree(src, os.path.join(cls.oc.temp_dir, item))
            cls.oc.addpath(cls.oc.temp_dir)
        else:
            cls.oc.addpath(tests_dir)

    @classmethod
    def teardown_class(cls):
        cls.oc.exit()

    def test_unicode_docstring(self):
        """Make sure unicode docstrings in Octave functions work"""
        help(self.oc.test_datatypes)

    def test_loadmat_typeerror_raises_oct2pyerror(self):
        """scipy TypeError for char encoding bug in old Octave becomes Oct2PyError (#179)."""
        from unittest.mock import patch

        from oct2py.io import read_file

        with (
            patch(
                "oct2py.io.loadmat",
                side_effect=TypeError("buffer is too small for requested array"),
            ),
            pytest.raises(Oct2PyError, match="character-encoding bug in older Octave"),
        ):
            read_file("/nonexistent.mat")

    def test_context_manager(self):
        """Make sure oct2py works within a context manager"""
        with Oct2Py() as oc1:
            ones = oc1.ones(1)
        assert ones == np.ones(1)
        with Oct2Py() as oc2:
            ones = oc2.ones(1)
        assert ones == np.ones(1)

    def test_singleton_sparses(self):
        """Make sure a singleton sparse matrix works"""
        import scipy.sparse

        data = scipy.sparse.csc_matrix(1)
        self.oc.push("x", data)
        assert np.allclose(data.toarray(), self.oc.pull("x").toarray())
        self.oc.push("y", [data])
        y = self.oc.pull("y")
        assert np.allclose(data.toarray(), y[0].toarray())

    def test_logging(self):
        # create a stringio and a handler to log to it
        def get_handler():
            sobj = StringIO()
            hdlr = logging.StreamHandler(sobj)
            hdlr.setLevel(logging.DEBUG)
            return hdlr

        hdlr = get_handler()
        self.oc.logger.addHandler(hdlr)

        # generate some messages (logged and not logged)
        self.oc.ones(1, verbose=True)

        self.oc.logger.setLevel(logging.DEBUG)
        self.oc.zeros(1)

        # check the output
        lines = hdlr.stream.getvalue().strip().split("\n")
        resp = "\n".join(lines)
        assert 'exist("zeros")' in resp
        assert 'exist("ones")' not in resp
        assert "_pyeval(" in resp

        # now make an object with a desired logger
        logger = oct2py.get_log("test")
        hdlr = get_handler()
        logger.addHandler(hdlr)
        logger.setLevel(logging.INFO)
        with Oct2Py(logger=logger) as oc2:
            # generate some messages (logged and not logged)
            oc2.ones(1, verbose=True)
            oc2.logger.setLevel(logging.DEBUG)
            oc2.zeros(1)

        # check the output
        lines = hdlr.stream.getvalue().strip().split("\n")
        resp = "\n".join(lines)
        assert 'exist("zeros")' in resp
        assert 'exist("ones")' not in resp
        assert "_pyeval(" in resp

    def test_demo(self):
        if self._flatpak:
            pytest.skip("not supported inside flatpak sandbox")
        from oct2py import demo

        try:
            demo.demo(0.01, interactive=False)  # type:ignore[attr-defined]
        except AttributeError:
            demo(0.01, interactive=False)

    def test_threads(self):
        from oct2py import thread_check

        try:
            thread_check()
        except TypeError:
            thread_check.thread_check()  # type:ignore[attr-defined]

    def test_threadpool_no_process_leak(self):
        """Oct2Py sessions created in a ThreadPoolExecutor must not leak Octave
        subprocesses after the threads complete (issue #289)."""
        import psutil

        proc = psutil.Process(os.getpid())
        initial = len(proc.children(recursive=True))

        def run():
            oc = Oct2Py()
            result = oc.sum([1, 2, 3])
            return result

        for _ in range(2):
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(run) for _ in range(3)]
                for future in as_completed(futures):
                    future.result()
            gc.collect()

        final = len(proc.children(recursive=True))
        assert final <= initial + 1, (
            f"Octave process leak detected: started with {initial} children, ended with {final}"
        )

    @pytest.mark.skipif(sys.platform == "win32", reason="fork not available on Windows")
    def test_multiprocessing_pool(self):
        """Oct2Py sessions created in a multiprocessing.Pool must work (issue #283).

        When Pool uses fork, child processes inherit the parent's pexpect pty
        file descriptors and Octave process PID.  Calling exit() on the
        inherited session in a child sends SIGHUP to the parent's Octave
        process, killing it.  Oct2Py must reset inherited sessions after fork
        so the parent's session is not destroyed.
        """
        import multiprocessing

        import oct2py as _oct2py

        # Verify parent's global session works before the fork.
        assert float(_oct2py.octave.sum([1, 2, 3])) == 6.0

        ctx = multiprocessing.get_context("fork")
        with ctx.Pool(3) as pool:
            results = pool.map(_multiprocessing_worker_exit, range(3))

        assert results == [6.0, 6.0, 6.0]

        # After the pool, the parent's global session must still be alive.
        assert float(_oct2py.octave.sum([4, 5, 6])) == 15.0

    def test_speed_check(self):
        from oct2py import speed_check

        try:
            speed_check()
        except TypeError:
            speed_check.speed_check()  # type:ignore[attr-defined]

    def test_plot(self):
        if self._flatpak:
            pytest.skip("not supported inside flatpak sandbox")
        plot_dir = tempfile.mkdtemp(dir=self.oc.temp_dir).replace("\\", "/")
        self.oc.plot([1, 2, 3], plot_dir=plot_dir)
        assert glob.glob("%s/*" % plot_dir)
        assert self.oc.extract_figures(plot_dir)

    @pytest.mark.skipif(sys.platform != "linux", reason="Linux only")
    def test_plot_via_eval(self):
        """Figures created by plot() inside eval() must be captured via plot_dir (issue #158).

        Calling octave.eval('plot(...)') should expose the same plot-capture
        behaviour as octave.plot(...): when plot_dir is provided the figure is
        saved to disk; when it is not, the interactive drawnow('expose') path
        in _pyeval.m handles display.
        """
        if self.oc._engine.executable.startswith("flatpak"):
            raise pytest.skip("Flatpak version of octave does not handle plotting")
        if "snap" in self.oc._engine.executable:
            raise pytest.skip("snap version of octave does not handle plotting")
        plot_dir = tempfile.mkdtemp().replace("\\", "/")
        self.oc.eval("plot([1, 2, 3])", plot_dir=plot_dir)
        assert glob.glob("%s/*" % plot_dir), "No figure files saved from eval() plot"
        assert self.oc.extract_figures(plot_dir), "extract_figures returned nothing"

    def test_plot_from_inside_m_file(self):
        """Test that plots generated inside a .m function are captured via plot_dir (issue #172).

        When a .m file creates figures internally (e.g. clf/subplot/plot/pause),
        passing plot_dir to feval should save those figures even though the
        rendering happens inside the Octave subprocess.
        """
        if self._flatpak:
            pytest.skip("not supported inside flatpak sandbox")
        plot_dir = tempfile.mkdtemp(dir=self.oc.temp_dir).replace("\\", "/")
        m_path = os.path.join(self.oc.temp_dir, "test_plot_inside.m")
        with open(m_path, "w") as f:
            f.write(
                "function test_plot_inside()\n"
                "  clf;\n"
                "  subplot(2,1,1);\n"
                "  plot([1 2 3], [4 5 6]);\n"
                "  subplot(2,1,2);\n"
                "  plot([1 2 3], [6 5 4]);\n"
                "end\n"
            )
        try:
            self.oc.feval(m_path, nout=0, plot_dir=plot_dir)
            assert glob.glob("%s/*" % plot_dir), "No figure files saved from inside .m function"
            assert self.oc.extract_figures(plot_dir), "extract_figures returned nothing"
        finally:
            os.unlink(m_path)

    def test_interactive_figure(self):
        """Test that figures created via eval() are accessible (issues #176, #158).

        Interactive figure display (drawnow expose) is handled inside _pyeval.m
        when figures are open and figure visibility is on.  This covers both the
        direct-call path (oc.figure()) and the eval() path (oc.eval("plot(...)"))
        to ensure issue #158 is addressed: plots created inside eval() must be
        visible to Octave's figure system, not silently dropped.
        """
        if self._flatpak:
            pytest.skip("not supported inside flatpak sandbox")
        oc = Oct2Py(backend="default")
        oc.figure(1)
        n_figs = oc.eval("numel(get(0, 'children'))", nout=1)
        assert int(n_figs) >= 1, "Expected at least one open figure after figure(1)"

        # Verify that a plot created via eval() also registers as a figure (issue #158).
        oc.eval("figure(2); plot([1, 2, 3]);")
        n_figs_after = oc.eval("numel(get(0, 'children'))", nout=1)
        assert int(n_figs_after) >= 2, "Expected at least two open figures after eval('plot(...)')"

        oc.eval("close all")
        oc.exit()

    def test_show(self):
        """Test _show_figures() end-to-end using matplotlib's inline backend (issue #164).

        Exercises the real capture path: Octave renders a figure to a PNG in
        temp_dir, which is loaded by matplotlib and added as a figure.  The
        IPython inline backend is used so plt.show() flushes figures to display
        output without opening a window.  A spy on plt.show() captures the
        figure count at the moment of display, since the inline backend clears
        figures immediately after show().
        """
        if self._flatpak:
            pytest.skip("not supported inside flatpak sandbox")
        from unittest.mock import patch

        import matplotlib as mpl
        import matplotlib.pyplot as plt

        mpl.use("module://matplotlib_inline.backend_inline")
        plt.close("all")

        oc = Oct2Py(backend="inline")
        try:
            # A real plot creates a figure that _show_figures() should capture.
            oc.plot([1, 2, 3])

            captured: list[int] = []

            def spy_show(*args: object, **kwargs: object) -> None:
                captured.append(len(plt.get_fignums()))

            with patch.object(plt, "show", spy_show):
                oc._show_figures()
            assert captured and captured[0] > 0, (
                "_show_figures() did not create any matplotlib figures"
            )

            # With no open Octave figures, _show_figures() should not call plt.show().
            oc.eval("close all", nout=0)
            captured.clear()
            with patch.object(plt, "show", spy_show):
                oc._show_figures()
            assert not captured, "_show_figures() called plt.show() unexpectedly"
        finally:
            oc.exit()

        # auto_show=True: _show_figures() fires after each feval that produces a figure.
        plt.close("all")
        oc2 = Oct2Py(backend="inline", auto_show=True)
        try:
            captured = []
            with patch.object(plt, "show", spy_show):
                oc2.plot([1, 2, 3])
            assert captured and captured[0] > 0, (
                "auto_show=True did not produce a matplotlib figure after plot()"
            )
        finally:
            oc2.exit()
            plt.close("all")

    def test_show_no_engine(self):
        """_show_figures() is a no-op when _engine is None (closed session)."""
        oc = Oct2Py()
        oc.exit()  # sets _engine = None
        oc._show_figures()  # must return silently without error

    def test_disable_backend(self):
        """backend='disable' suppresses all figure rendering (issue #152)."""
        if self._flatpak:
            pytest.skip("not supported inside flatpak sandbox")
        from unittest.mock import patch

        oc = Oct2Py(backend="disable")
        try:
            # Basic computation must still work.
            result = oc.eval("1 + 1", nout=1)
            assert result == 2

            # auto_show must default to False.
            assert not oc._auto_show

            # make_figures must never be called when backend='disable'.
            with patch.object(oc._engine, "make_figures") as mock_mf:
                oc.eval("figure(1); plot([1,2,3]);", nout=0)
                mock_mf.assert_not_called()

            # show() must be a silent no-op.
            oc.show()
        finally:
            oc.exit()

    def test_narg_out(self):
        if self._flatpak:
            pytest.skip("Flatpak version of octave does not handle svd")
        s = self.oc.svd(np.array([[1, 2], [1, 3]]))
        assert s.shape == (2, 1)
        U, S, V = self.oc.svd([[1, 2], [1, 3]], nout=3)
        assert U.shape == S.shape == V.shape == (2, 2)

    def test_help(self):
        help(self.oc)

    def test_trailing_underscore(self):
        x = self.oc.ones_()
        assert np.allclose(x, np.ones(1))

    def test_pandas_series(self):
        data = [1, 2, 3, 4, 5, 6]
        series = pd.Series(data)
        self.oc.push("x", series)
        assert np.allclose(data, self.oc.pull("x"))

    def test_panda_dataframe(self):
        data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        df = pd.DataFrame(data, columns=["a", "b", "c"])
        self.oc.push("y", df)
        assert np.allclose(data, self.oc.pull("y"))

    def test_using_exited_session(self):
        with Oct2Py() as oc:
            oc.exit()
            with pytest.raises(Oct2PyError):
                oc.eval("ones")

    # def test_keyboard(self):
    #     self.oc.eval('a=1')

    #     stdin = sys.stdin
    #     sys.stdin = StringIO('a\ndbquit\n')

    #     try:
    #         self.oc.keyboard(timeout=3)
    #     except Oct2PyError as e:  # pragma: no cover
    #         if 'session timed out' in str(e).lower():
    #             # the keyboard command is not supported
    #             # (likely using Octave 3.2)
    #             return
    #         else:
    #             raise(e)
    #     sys.stdin.flush()
    #     sys.stdin = stdin

    #     self.oc.pull('a') == 1

    def test_func_without_docstring(self):
        out = self.oc.test_nodocstring(5)
        assert out == 5
        doc = self.oc.test_nodocstring.__doc__
        assert "user-defined function" in doc or "undocumented function" in doc
        expected_dir = self.oc.temp_dir if self._flatpak else os.path.dirname(__file__)
        assert expected_dir in doc

    def test_func_noexist(self):
        with pytest.raises(Oct2PyError):
            self.oc.eval("oct2py_dummy")

    def test_timeout(self):
        if self._flatpak:
            pytest.skip("not supported inside flatpak sandbox")
        with Oct2Py(timeout=2) as oc:
            oc.pause(2.1, timeout=5, nout=0)
            with pytest.raises(Oct2PyError):
                oc.pause(3, nout=0)

    def test_call_path(self):
        with Oct2Py() as oc:
            oc.addpath(os.path.dirname(__file__))
            DATA = oc.test_datatypes()
        assert DATA.string.basic == "spam"

    def test_long_variable_name(self):
        name = "this_variable_name_is_over_32_char"
        self.oc.push(name, 1)
        x = self.oc.pull(name)
        assert x == 1

    def test_syntax_error_embedded(self):
        with pytest.raises(Oct2PyError):
            self.oc.eval("""eval("a='1")""")
        self.oc.push("b", 1)
        x = self.oc.pull("b")
        assert x == 1

    def test_oned_as(self):
        x = np.ones(10)
        self.oc.push("x", x)
        assert self.oc.pull("x").shape == x[:, np.newaxis].T.shape
        oc = Oct2Py(oned_as="column")
        oc.push("x", x)
        assert oc.pull("x").shape == x[:, np.newaxis].shape
        oc.exit()

    def test_temp_dir(self):
        temp_dir = tempfile.mkdtemp(dir=self.oc.temp_dir)
        oc = Oct2Py(temp_dir=temp_dir)
        oc.push("a", 1)
        assert len(os.listdir(temp_dir))
        shutil.rmtree(temp_dir, ignore_errors=True)
        oc.exit()

    def test_clear(self):
        """Make sure clearing variables does not mess anything up."""
        self.oc.eval("clear()")
        with pytest.raises(Oct2PyError):
            self.oc.__getattr__("clear")
        with pytest.raises(Oct2PyError):
            self.oc.feval("clear")

    def test_multiline_statement(self):
        sobj = StringIO()
        hdlr = logging.StreamHandler(sobj)
        hdlr.setLevel(logging.DEBUG)
        self.oc.logger.addHandler(hdlr)

        self.oc.logger.setLevel(logging.DEBUG)

        ans = self.oc.eval(
            """
    a =1
    a + 1;
    b = 3
    b + 1"""
        )
        text = hdlr.stream.getvalue().strip()
        self.oc.logger.removeHandler(hdlr)
        assert ans == 4
        lines = text.splitlines()
        lines = [line.replace("  ", " ") for line in lines]
        assert lines[-1] == "ans = 4"
        assert lines[-2] == "b = 3"
        assert lines[-3] == "a = 1"

    def test_empty_values(self):
        self.oc.push("a", "")
        assert not self.oc.pull("a")

        self.oc.push("a", [])
        assert self.oc.pull("a") == []

        self.oc.push("a", None)
        assert np.isnan(self.oc.pull("a"))

        assert self.oc.struct() == [None]

    def test_deprecated_log(self):
        sobj = StringIO()
        hdlr = logging.StreamHandler(sobj)
        hdlr.setLevel(logging.DEBUG)
        self.oc.logger.addHandler(hdlr)

        self.oc.logger.setLevel(logging.DEBUG)
        self.oc.eval('disp("hi")', log=False)
        text = hdlr.stream.getvalue().strip()
        assert not text
        self.oc.logger.removeHandler(hdlr)

    def test_deprecated_return_both(self):
        text, value = self.oc.eval(['disp("hi")', "ones(3);"], return_both=True)
        assert text.strip() == "hi"
        assert np.allclose(value, np.ones((3, 3)))

        lines: list[str] = []
        text, value = self.oc.eval(
            ['disp("hi")', "ones(3);"], return_both=True, stream_handler=lines.append
        )
        assert not text
        assert np.allclose(value, np.ones((3, 3)))
        assert lines[0].strip() == "hi"

    def test_logger(self):
        logger = self.oc.logger
        self.oc.logger = None
        assert self.oc.logger is not None
        assert self.oc.logger == logger  # type:ignore[unreachable]

    def test_struct_array(self):
        self.oc.eval('x = struct("y", {1, 2}, "z", {3, 4});')
        x = self.oc.pull("x")
        assert set(x.fieldnames) == {"y", "z"}
        other = StructArray(x)
        assert other.shape == x.shape

    def test_feval_script_default_nout(self):
        """Calling a .m script (not a function) with default nout should work (issue #332)."""
        result = self.oc.feval("test_octave_script")
        assert result is None

    @pytest.mark.skipif(
        sys.platform == "darwin",
        reason="macOS pre-allocates an 8 MB main-thread stack for the Octave "
        "subprocess that cannot be enlarged from Python",
    )
    def test_recursive_function(self):
        """Recursive functions should work for deep recursion (issue #326)."""
        n = 300
        result = self.oc.test_recurse(n)
        assert result == n * (n + 1) / 2

    def test_struct_function_handle_field_converted(self):
        """Bug #215 (3/3): function handle fields in structs were silently dropped.

        save_safe_struct fell back to clean_struct, which called rmfield on any
        field whose class was not in the narrow acceptable_types list.  A function
        handle therefore vanished from the result.  The fix converts function
        handles to their string representation via func2str instead of dropping.
        """
        self.oc.eval(
            "function r = _make_fh_struct(); r.fn = @(x) x^2; r.val = 42.0; end",
            nout=0,
        )
        result = self.oc._make_fh_struct()
        assert result.val == 42.0
        # fn must be present and contain the function-handle string, not be absent
        assert "@" in result.fn

    def test_struct_integer_fields_preserved(self):
        """Bug #215 (1/3): acceptable_types was missing integer and single types.

        When save_safe_struct fell back to the cleaning path, only
        {'double', 'char', 'logical', 'sparse'} were kept.  Integer-typed fields
        (int8/16/32/64, uint8/16/32/64) and single-precision fields were therefore
        discarded even though MAT v6 supports them.  The fix adds all numeric
        primitive types to the list.
        """
        self.oc.eval(
            "function r = _make_int_struct();"
            " r.fn = @(x) x; r.count = int32(99); r.flag = uint8(1); end",
            nout=0,
        )
        result = self.oc._make_int_struct()
        assert int(result.count) == 99
        assert int(result.flag) == 1

    def test_toplevel_unserializable_value_coerced(self):
        """Bug #215 (2/3): non-struct/non-cell top-level values were not cleaned.

        The old save_safe_struct catch block only cleaned result{1,1} when it was
        a struct or a cell.  If the top-level value was something else (e.g. a bare
        function handle), neither branch fired, and the second save attempt also
        failed, raising an Oct2PyError.  The fix applies coerce_value unconditionally.
        """
        # A bare function handle as the return value triggers the fallback; the old
        # code raised Oct2PyError here because neither isstruct nor iscell matched.
        result = self.oc.feval("eval", "@(x) x + 1", nout=1)
        assert isinstance(result, str)
        assert "@" in result

    def test_classdef_object_return(self):
        """Returning a classdef object must not raise an error (issue #215).

        Octave 11+ auto-converts classdef objects to structs on save, so the
        result is a Struct and property values are accessible directly.  Older
        Octave versions preserve the classdef identity and return an
        OctaveUserClass; in that case we just verify a usable object came back.
        """
        from oct2py.io import Struct

        result = self.oc.feval("SimpleObj", 7, "hi", nout=1)
        assert result is not None
        if isinstance(result, Struct):
            # Octave 11+: classdef converted to struct on save
            assert int(result.value) == 7
            assert result.label == "hi"
        # else: older Octave returns OctaveUserClass — non-crash is sufficient

    def test_classdef_required_ctor_return(self):
        """Returning a classdef whose constructor requires arguments must not raise (issue #174).

        Previously, _make_user_class called fieldnames(ClassName) which tries
        to invoke the no-arg constructor.  For classes that require arguments
        that raised an Oct2PyError.  The fix passes dtype.names from the
        MatlabObject directly so fieldnames() is never called.
        """
        from oct2py.io import Struct

        result = self.oc.feval("NoDefaultCtorClass", 5, "test", nout=1)
        assert result is not None
        if isinstance(result, Struct):
            # Octave 11+: classdef converted to struct on save
            assert int(result.value) == 5
            assert result.label == "test"
        # else: older Octave returns OctaveUserClass — non-crash is sufficient

    def test_eval_quiet_discards_output(self):
        """quiet=True should execute the command but return None (issue #211)."""
        self.oc.push("x", 42)
        result = self.oc.eval("x", quiet=True)
        assert result is None
        # Confirm default behaviour still returns ans for an expression
        assert self.oc.eval("x + 0") == 42

    def test_feval_quiet_discards_output(self):
        """feval quiet=True should execute but return None (issue #211)."""
        result = self.oc.feval("max", np.array([3, 1, 2]), quiet=True)
        assert result is None

    def test_workspace_proxy(self):
        """workspace attribute should support dict-style get/set/delete (issue #190)."""
        self.oc.eval("x = 5", nout=0)
        assert self.oc.workspace["x"] == 5.0

        self.oc.workspace["y"] = 42
        assert self.oc.pull("y") == 42.0

        del self.oc.workspace["y"]
        with pytest.raises(Oct2PyError):
            self.oc.pull("y")

        # Deleting a non-variable (e.g. a built-in function, exist != 1) raises KeyError
        with pytest.raises(KeyError):
            del self.oc.workspace["sin"]

    def test_feval_script_with_args(self):
        """Calling a .m script with args should make them available via argv (issue #332)."""
        lines: list[str] = []
        self.oc.feval(
            "test_octave_script_argv",
            "hello_from_oct2py",
            nout=0,
            stream_handler=lines.append,
        )
        assert any("hello_from_oct2py" in line for line in lines)

    def test_restart_preserves_sigint_handler(self):
        """restart() must not permanently alter the SIGINT disposition (issue #168).

        If a third-party library (e.g. an older scipy/sympy) transiently sets
        SIGINT to SIG_IGN and the pexpect spawn captures that transient value,
        the spawn's finally block can "restore" SIG_IGN after the library has
        already corrected it.  Oct2Py's restart() must restore whatever handler
        was in place before the spawn so that it has no net effect on SIGINT.
        """
        original = signal.getsignal(signal.SIGINT)
        try:
            # Simulate a library that leaves SIGINT=SIG_IGN before Oct2Py starts.
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            oc = Oct2Py()
            oc.exit()
            assert signal.getsignal(signal.SIGINT) is signal.SIG_IGN
        finally:
            signal.signal(signal.SIGINT, original)

    def test_restart_preserves_custom_sigint_handler(self):
        """restart() restores a custom SIGINT handler unchanged (issue #168)."""
        original = signal.getsignal(signal.SIGINT)
        sentinel = []

        def custom_handler(signum, frame):  # pragma: no cover
            sentinel.append(signum)

        try:
            signal.signal(signal.SIGINT, custom_handler)
            oc = Oct2Py()
            oc.exit()
            assert signal.getsignal(signal.SIGINT) is custom_handler
        finally:
            signal.signal(signal.SIGINT, original)

    def test_old_style_octave_object_return(self):
        """Returning an old-style Octave object must not raise an error (issue #166).

        Octave can save old-style class instances (e.g. ``ss`` from the control
        package) without raising an exception, but the resulting MAT file
        contains an Octave-specific type tag (miINT8/type 6) that scipy's
        ``loadmat`` cannot parse.  The fix verifies readability via a round-trip
        load in Octave and applies coerce_value when the check fails.
        """
        pytest.importorskip("oct2py")  # always available; guards the skip logic below
        # Check whether the control package is installed.
        try:
            self.oc.eval("pkg load control", nout=0)
        except Oct2PyError:
            pytest.skip("Octave control package not installed")

        # Prior to the fix this raised:
        #   Oct2PyError: Expecting miMATRIX type here, got 6
        result = self.oc.ss(1)
        # The result should be coerced to a dict-like Struct (or similar
        # mapping) containing the state-space matrices.
        assert result is not None

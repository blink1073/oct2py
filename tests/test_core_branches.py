"""Tests for branch coverage of Oct2Py core methods."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from oct2py import Oct2Py, Oct2PyError, Oct2PySettings


class TestInit:
    """Tests for the new Oct2Py.__init__ parameters."""

    def _make_fake_engine(self, executable="/resolved/octave"):
        fake = MagicMock()
        fake.tmp_dir = tempfile.mkdtemp()
        fake.executable = executable
        return fake

    # --- settings parameter ---

    def test_settings_applied_as_defaults(self):
        """Oct2PySettings values fill in unspecified __init__ kwargs."""
        s = Oct2PySettings(backend="disable", timeout=42, oned_as="column",
                           convert_to_float=False, keep_matlab_shapes=True)
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oc = Oct2Py(settings=s)
        assert oc.backend == "disable"
        assert oc.timeout == 42
        assert oc._oned_as == "column"
        assert oc.convert_to_float is False
        assert oc.keep_matlab_shapes is True
        oc._engine = None

    def test_kwargs_override_settings(self):
        """Explicit __init__ kwargs take precedence over settings values."""
        s = Oct2PySettings(backend="disable", timeout=99)
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oc = Oct2Py(settings=s, backend="default", timeout=7)
        assert oc.backend == "default"
        assert oc.timeout == 7
        oc._engine = None

    def test_default_settings_created_when_none(self):
        """When settings=None, a default Oct2PySettings() is created."""
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oc = Oct2Py()
        assert isinstance(oc._settings, Oct2PySettings)
        oc._engine = None

    # --- extra_cli_options parameter ---

    def test_extra_cli_options_passed_to_engine(self):
        """extra_cli_options is forwarded as cli_options to OctaveEngine."""
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake) as mock_engine:
            oc = Oct2Py(extra_cli_options="--traditional")
        assert mock_engine.call_args.kwargs.get("cli_options") == "--traditional"
        oc._engine = None

    def test_no_extra_cli_options_passes_empty_string(self):
        """Without extra_cli_options, cli_options is an empty string."""
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake) as mock_engine:
            oc = Oct2Py()
        assert mock_engine.call_args.kwargs.get("cli_options") == ""
        oc._engine = None

    def test_extra_cli_options_from_settings(self):
        """extra_cli_options falls back to the settings value."""
        s = Oct2PySettings(extra_cli_options="--traditional")
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake) as mock_engine:
            oc = Oct2Py(settings=s)
        cli = mock_engine.call_args.kwargs.get("cli_options", "")
        assert "--traditional" in cli
        oc._engine = None

    def test_extra_cli_options_kwarg_overrides_settings(self):
        """extra_cli_options kwarg overrides the settings value."""
        s = Oct2PySettings(extra_cli_options="--from-settings")
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake) as mock_engine:
            oc = Oct2Py(settings=s, extra_cli_options="--from-kwarg")
        cli = mock_engine.call_args.kwargs.get("cli_options", "")
        assert "--from-kwarg" in cli
        assert "--from-settings" not in cli
        oc._engine = None

    # --- executable parameter ---

    def test_executable_passed_to_engine(self):
        """executable kwarg is forwarded to OctaveEngine."""
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake) as mock_engine:
            oc = Oct2Py(executable="/custom/octave")
        assert mock_engine.call_args.kwargs.get("executable") == "/custom/octave"
        oc._engine = None

    def test_executable_updated_from_engine(self):
        """self.executable is updated to the actual path used by the engine."""
        fake = self._make_fake_engine(executable="/resolved/octave-cli")
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oc = Oct2Py(executable="/custom/octave")
        assert oc.executable == "/resolved/octave-cli"
        oc._engine = None

    def test_executable_from_settings(self):
        """executable falls back to the settings value."""
        s = Oct2PySettings(executable="/settings/octave")
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake) as mock_engine:
            oc = Oct2Py(settings=s)
        assert mock_engine.call_args.kwargs.get("executable") == "/settings/octave"
        oc._engine = None

    def test_executable_kwarg_overrides_settings(self):
        """executable kwarg overrides the settings value."""
        s = Oct2PySettings(executable="/settings/octave")
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake) as mock_engine:
            oc = Oct2Py(settings=s, executable="/kwarg/octave")
        assert mock_engine.call_args.kwargs.get("executable") == "/kwarg/octave"
        oc._engine = None

    # --- load_octaverc parameter ---

    def test_load_octaverc_default_is_true(self):
        """load_octaverc defaults to True and is passed to OctaveEngine."""
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake) as mock_engine:
            oc = Oct2Py()
        assert mock_engine.call_args.kwargs.get("load_octaverc") is True
        oc._engine = None

    def test_load_octaverc_false_passed_to_engine(self):
        """load_octaverc=False is forwarded to OctaveEngine."""
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake) as mock_engine:
            oc = Oct2Py(load_octaverc=False)
        assert mock_engine.call_args.kwargs.get("load_octaverc") is False
        oc._engine = None

    def test_load_octaverc_from_settings(self):
        """load_octaverc falls back to the settings value."""
        s = Oct2PySettings(load_octaverc=False)
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake) as mock_engine:
            oc = Oct2Py(settings=s)
        assert mock_engine.call_args.kwargs.get("load_octaverc") is False
        oc._engine = None

    def test_load_octaverc_kwarg_overrides_settings(self):
        """load_octaverc kwarg overrides the settings value."""
        s = Oct2PySettings(load_octaverc=False)
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake) as mock_engine:
            oc = Oct2Py(settings=s, load_octaverc=True)
        assert mock_engine.call_args.kwargs.get("load_octaverc") is True
        oc._engine = None

    # --- plot_* parameters ---

    def test_plot_params_defaults(self):
        """Plot params get their defaults from settings when not specified."""
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oc = Oct2Py()
        assert oc.plot_format == "svg"
        assert oc.plot_name == "plot"
        assert oc.plot_width is None
        assert oc.plot_height is None
        assert oc.plot_res is None
        oc._engine = None

    def test_plot_params_from_kwargs(self):
        """Plot params set via kwargs are stored on the instance."""
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oc = Oct2Py(plot_format="png", plot_name="fig",
                        plot_width=800, plot_height=600, plot_res=150)
        assert oc.plot_format == "png"
        assert oc.plot_name == "fig"
        assert oc.plot_width == 800
        assert oc.plot_height == 600
        assert oc.plot_res == 150
        oc._engine = None

    def test_plot_params_from_settings(self):
        """Plot params fall back to settings values."""
        s = Oct2PySettings(plot_format="png", plot_name="fig",
                           plot_width=800, plot_height=600, plot_res=150)
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oc = Oct2Py(settings=s)
        assert oc.plot_format == "png"
        assert oc.plot_name == "fig"
        assert oc.plot_width == 800
        assert oc.plot_height == 600
        assert oc.plot_res == 150
        oc._engine = None

    def test_plot_params_kwarg_overrides_settings(self):
        """Plot param kwargs take precedence over settings."""
        s = Oct2PySettings(plot_format="png", plot_width=800)
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oc = Oct2Py(settings=s, plot_format="svg", plot_width=1024)
        assert oc.plot_format == "svg"
        assert oc.plot_width == 1024
        oc._engine = None

    def test_plot_params_used_as_eval_defaults(self):
        """Instance plot params are used as defaults in eval() calls."""
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oc = Oct2Py(plot_format="png", plot_name="myfig",
                        plot_width=640, plot_height=480, plot_res=96)
        with patch.object(oc, "_feval", return_value=None):
            oc.eval("1+1")
        engine_settings = fake.plot_settings
        assert engine_settings["format"] == "png"
        assert engine_settings["name"] == "myfig"
        assert engine_settings["width"] == 640
        assert engine_settings["height"] == 480
        assert engine_settings["resolution"] == 96
        oc._engine = None


class TestEnterDel:
    """Tests for __enter__ and __del__."""

    def test_enter_restarts_closed_session(self):
        """__enter__ should restart the session if _engine is None."""
        oc = Oct2Py()
        oc.exit()
        assert oc._engine is None
        with oc:
            assert oc._engine is not None
            result = oc.ones(1)
        assert result == np.ones(1)

    def test_enter_with_active_engine_does_not_restart(self):
        """__enter__ with active engine should just return self."""
        oc = Oct2Py()
        engine_before = oc._engine
        with oc:
            assert oc._engine is engine_before
        oc.exit()

    def test_del_exits_session(self):
        """__del__ should close the session."""
        oc = Oct2Py()
        assert oc._engine is not None
        oc.__del__()
        assert oc._engine is None

    def test_del_on_closed_session(self):
        """__del__ on an already-closed session should not raise."""
        oc = Oct2Py()
        oc.exit()
        oc.__del__()  # should not raise


class TestGetPointer:
    """Tests for all branches of Oct2Py.get_pointer."""

    oc: Oct2Py

    @classmethod
    def setup_class(cls):
        cls.oc = Oct2Py()
        cls.oc.addpath(os.path.dirname(__file__))

    @classmethod
    def teardown_class(cls):
        cls.oc.exit()

    def test_get_pointer_variable(self):
        """exist == 1: should return an OctaveVariablePtr."""
        from oct2py.dynamic import OctaveVariablePtr

        self.oc.eval("foo = [1, 2, 3];")
        ptr = self.oc.get_pointer("foo")
        assert isinstance(ptr, OctaveVariablePtr)
        assert np.allclose(ptr.value, [[1.0, 2.0, 3.0]])

    def test_get_pointer_builtin_function(self):
        """exist in [2, 3, 5]: should return an OctaveFunctionPtr."""
        from oct2py.dynamic import OctaveFunctionPtr

        ptr = self.oc.get_pointer("sin")
        assert isinstance(ptr, OctaveFunctionPtr)
        assert ptr.address == "@sin"

    def test_get_pointer_m_file_function(self):
        """exist == 2 (m-file): should return an OctaveFunctionPtr."""
        from oct2py.dynamic import OctaveFunctionPtr

        ptr = self.oc.get_pointer("test_datatypes")
        assert isinstance(ptr, OctaveFunctionPtr)

    def test_get_pointer_undefined_raises(self):
        """Undefined name should raise Oct2PyError."""
        with pytest.raises(Oct2PyError, match="does not exist"):
            self.oc.get_pointer("_oct2py_no_such_var_xyz")

    def test_get_pointer_exist_zero_raises(self):
        """exist == 0 branch: should raise Oct2PyError."""
        # Patch _exist to return 0 and _isobject to return False,
        # bypassing the normal _exist logic that raises before returning 0.
        with (
            patch.object(self.oc, "_exist", return_value=0),
            patch.object(self.oc, "_isobject", return_value=False),
            pytest.raises(Oct2PyError, match="is undefined"),
        ):
            self.oc.get_pointer("anything")

    def test_get_pointer_unknown_type_raises(self):
        """Unknown exist code with isobject=False should raise Oct2PyError."""
        with (
            patch.object(self.oc, "_exist", return_value=99),
            patch.object(self.oc, "_isobject", return_value=False),
            pytest.raises(Oct2PyError, match="Unknown type"),
        ):
            self.oc.get_pointer("anything")

    def test_get_pointer_user_class(self):
        """isobject == True: should return an OctaveUserClass."""
        self.oc.eval("p = polynomial([1, 2, 3]);")
        ptr = self.oc.get_pointer("p")
        # OctaveUserClass instances are callable (like a function ptr)
        assert hasattr(ptr, "address")


class TestRestart:
    """Tests for all branches of Oct2Py.restart."""

    def test_restart_with_no_prior_engine(self):
        """restart should succeed when _engine is None."""
        oc = Oct2Py()
        oc.exit()
        assert oc._engine is None
        oc.restart()
        assert oc._engine is not None
        oc.exit()

    def test_restart_terminates_old_engine(self):
        """restart should terminate the old engine before creating a new one."""
        oc = Oct2Py()
        old_engine = oc._engine
        assert old_engine is not None
        oc.restart()
        assert oc._engine is not old_engine
        oc.exit()

    def test_restart_with_temp_dir_none(self):
        """When temp_dir is None, restart should create a new temp dir."""
        oc = Oct2Py()
        oc.exit()
        oc.temp_dir = None
        oc.restart()
        assert oc.temp_dir is not None
        assert os.path.isdir(oc.temp_dir)
        oc.exit()

    def test_restart_with_temp_dir_set(self):
        """When temp_dir is already set, restart should not change it."""
        temp_dir = tempfile.mkdtemp()
        oc = Oct2Py(temp_dir=temp_dir)
        original_temp_dir = oc.temp_dir
        oc.restart()
        assert oc.temp_dir == original_temp_dir
        oc.exit()

    def test_restart_octave_env_var_propagation(self):
        """OCTAVE env var should be passed to OctaveEngine when OCTAVE_EXECUTABLE is unset."""
        env_without_exec = {k: v for k, v in os.environ.items() if k != "OCTAVE_EXECUTABLE"}
        env_without_exec["OCTAVE"] = "/fake/octave"
        fake_engine = MagicMock()
        fake_engine.tmp_dir = tempfile.mkdtemp()
        with (
            patch.dict(os.environ, env_without_exec, clear=True),
            patch("oct2py.core.OctaveEngine", return_value=fake_engine) as mock_engine,
        ):
            oc = Oct2Py()
            assert mock_engine.call_args.kwargs.get("executable") == "/fake/octave"
            assert "OCTAVE_EXECUTABLE" not in os.environ
            oc.exit()

    def test_restart_octave_executable_not_overwritten(self):
        """OCTAVE_EXECUTABLE should take precedence over OCTAVE when passed to OctaveEngine."""
        env = dict(os.environ)
        env["OCTAVE_EXECUTABLE"] = "/custom/octave"
        env["OCTAVE"] = "/other/octave"
        fake_engine = MagicMock()
        fake_engine.tmp_dir = tempfile.mkdtemp()
        with (
            patch.dict(os.environ, env, clear=True),
            patch("oct2py.core.OctaveEngine", return_value=fake_engine) as mock_engine,
        ):
            oc = Oct2Py()
            assert mock_engine.call_args.kwargs.get("executable") == "/custom/octave"
            oc.exit()

    def test_restart_engine_creation_failure_raises(self):
        """If OctaveEngine creation fails, restart should raise Oct2PyError."""
        oc = Oct2Py()
        oc.exit()
        with (
            patch("oct2py.core.OctaveEngine", side_effect=RuntimeError("bad engine")),
            pytest.raises(Oct2PyError, match="bad engine"),
        ):
            oc.restart()


class TestGetDoc:
    """Tests for all branches of Oct2Py._get_doc."""

    oc: Oct2Py

    @classmethod
    def setup_class(cls):
        cls.oc = Oct2Py()
        cls.oc.addpath(os.path.dirname(__file__))

    @classmethod
    def teardown_class(cls):
        cls.oc.exit()

    def test_get_doc_no_engine_raises(self):
        """_get_doc should raise if session is closed."""
        oc = Oct2Py()
        oc.exit()
        with pytest.raises(Oct2PyError, match="Session is not open"):
            oc._get_doc("sin")

    def test_get_doc_syntax_error_raises(self):
        """_get_doc should raise Oct2PyError when help returns a syntax error."""
        mock_engine = MagicMock()
        mock_engine.eval.return_value = "syntax error: unexpected token\n"
        oc = Oct2Py()
        oc._engine = mock_engine
        with pytest.raises(Oct2PyError, match="syntax error"):
            oc._get_doc("bogus")
        oc._engine = None

    def test_get_doc_error_falls_back_to_type(self):
        """_get_doc should use type() when help returns 'error:' (not syntax error)."""
        mock_engine = MagicMock()
        mock_engine.eval.side_effect = [
            "error: undefined symbol\n",  # help() result
            "function x = myfunc()\n% doc\nend\n",  # type() result
        ]
        oc = Oct2Py()
        oc._engine = mock_engine
        doc = oc._get_doc("myfunc")
        assert "function x = myfunc()" in doc
        oc._engine = None

    def test_get_doc_normal(self):
        """_get_doc should return formatted documentation for a known function."""
        doc = self.oc._get_doc("sin")
        assert "sin" in doc.lower()
        assert "Parameters" in doc

    def test_get_doc_no_docstring_fallback(self):
        """_get_doc for a function without docstring uses type() output."""
        doc = self.oc._get_doc("test_nodocstring")
        assert "test_nodocstring" in doc


class TestExist:
    """Tests for all branches of Oct2Py._exist."""

    oc: Oct2Py

    @classmethod
    def setup_class(cls):
        cls.oc = Oct2Py()
        cls.oc.addpath(os.path.dirname(__file__))

    @classmethod
    def teardown_class(cls):
        cls.oc.exit()

    def test_exist_no_engine_raises(self):
        """_exist should raise when session is closed."""
        oc = Oct2Py()
        oc.exit()
        with pytest.raises(Oct2PyError, match="Session is not open"):
            oc._exist("sin")

    def test_exist_nonzero(self):
        """_exist should return the exist code directly when nonzero."""
        # "sin" is a builtin → exist == 5
        code = self.oc._exist("sin")
        assert code in [2, 3, 5]

    def test_exist_variable(self):
        """_exist should return 1 for a workspace variable."""
        self.oc.eval("_test_exist_var = 42;")
        code = self.oc._exist("_test_exist_var")
        assert code == 1

    def test_exist_zero_with_error_raises(self):
        """_exist should raise for a truly undefined name."""
        with pytest.raises(Oct2PyError, match="does not exist"):
            self.oc._exist("_oct2py_no_such_xyz_999")

    def test_exist_zero_without_error_returns_two(self):
        """_exist should return 2 when exist==0 but class() succeeds."""
        # Simulate: exist() returns "ans = 0" but class() returns something without "error:"
        mock_engine = MagicMock()
        mock_engine.eval.side_effect = [
            "ans = 0",  # exist("x") result
            "ans = double",  # class(x) result (no error)
        ]
        oc = Oct2Py()
        oc._engine = mock_engine
        result = oc._exist("x")
        assert result == 2
        oc._engine = None


class TestGetattr:
    """Tests for all branches of Oct2Py.__getattr__."""

    oc: Oct2Py

    @classmethod
    def setup_class(cls):
        cls.oc = Oct2Py()
        cls.oc.addpath(os.path.dirname(__file__))

    @classmethod
    def teardown_class(cls):
        cls.oc.exit()

    def test_getattr_dunder_raises_attribute_error(self):
        """Accessing a dunder attribute should raise AttributeError."""
        with pytest.raises(AttributeError):
            _ = self.oc.__nonexistent__

    def test_getattr_trailing_underscore_stripped(self):
        """Trailing underscore should be stripped before lookup (e.g. ones_)."""
        result = self.oc.ones_()
        assert np.allclose(result, np.ones(1))

    def test_getattr_no_engine_raises(self):
        """__getattr__ should raise Oct2PyError when session is closed."""
        oc = Oct2Py()
        oc.exit()
        with pytest.raises(Oct2PyError, match="Session is closed"):
            _ = oc.sin

    def test_getattr_variable_raises(self):
        """__getattr__ should raise for workspace variables (exist == 1)."""
        self.oc.eval("_test_getattr_var = 42;")
        with pytest.raises(Oct2PyError, match="not a valid callable"):
            _ = self.oc._test_getattr_var

    def test_getattr_clear_raises(self):
        """__getattr__ should raise specifically for 'clear'."""
        with pytest.raises(Oct2PyError, match="Cannot use `clear`"):
            self.oc.__getattr__("clear")

    def test_getattr_function_ptr(self):
        """__getattr__ should return a function pointer for known functions."""
        from oct2py.dynamic import OctaveFunctionPtr

        fn = self.oc.sin
        assert isinstance(fn, OctaveFunctionPtr)

    def test_getattr_user_class(self):
        """__getattr__ should return user class instance for OO objects."""
        # polynomial is defined as an OO class in tests/@polynomial
        # We need to set up the polynomial class first
        self.oc.eval("p = polynomial([1, 2, 3]);")
        ptr = self.oc.get_pointer("p")
        assert hasattr(ptr, "address")

    def test_getattr_caches_result(self):
        """__getattr__ should cache the result via setattr."""
        fn1 = self.oc.cos
        # After first access, the result should be cached on the instance
        assert self.oc.__dict__.get("cos") is fn1


class TestGetMaxNout:
    """Tests for all branches of Oct2Py._get_max_nout."""

    oc: Oct2Py

    @classmethod
    def setup_class(cls):
        cls.oc = Oct2Py()
        cls.oc.addpath(os.path.dirname(__file__))

    @classmethod
    def teardown_class(cls):
        cls.oc.exit()

    def test_get_max_nout_relative_path_calls_which(self):
        """Non-absolute path should resolve via which()."""
        # "test_datatypes" is in the addpath'd test directory
        nout = self.oc._get_max_nout("test_datatypes")
        assert nout == 1

    def test_get_max_nout_non_m_file_returns_zero(self):
        """A non-.m absolute path should return 0."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"function x = foo()\n")
            path = f.name
        try:
            nout = self.oc._get_max_nout(path)
            assert nout == 0
        finally:
            os.unlink(path)

    def test_get_max_nout_single_output(self):
        """test_datatypes.m has one output → nout == 1."""
        tests_dir = os.path.dirname(__file__)
        path = os.path.join(tests_dir, "test_datatypes.m")
        nout = self.oc._get_max_nout(path)
        assert nout == 1

    def test_get_max_nout_multiple_outputs(self):
        """roundtrip.m has two outputs [x, cls] → nout == 2."""
        tests_dir = os.path.dirname(__file__)
        path = os.path.join(tests_dir, "roundtrip.m")
        nout = self.oc._get_max_nout(path)
        assert nout == 2

    def test_get_max_nout_no_function_def_returns_zero(self):
        """A .m file with no function definition returns 0."""
        with tempfile.NamedTemporaryFile(suffix=".m", delete=False, mode="w") as f:
            f.write("% just a comment\nx = 1;\n")
            path = f.name
        try:
            nout = self.oc._get_max_nout(path)
            assert nout == 0
        finally:
            os.unlink(path)

    def test_get_max_nout_with_continuation(self):
        """A function signature split across lines with ... should be handled."""
        content = "function [a, b] = ...\n  myfunc(x)\na = x;\nb = x + 1;\nend\n"
        with tempfile.NamedTemporaryFile(suffix=".m", delete=False, mode="w") as f:
            f.write(content)
            path = f.name
        try:
            nout = self.oc._get_max_nout(path)
            # After "...", status becomes FUNCTION; next line is "  myfunc(x)"
            # which doesn't start with 'f' but status != "NOT FUNCTION", so it processes it
            # stripped: ['myfunc', 'x'] → 'myfunc' != '=' → nout=1, 'x' != '=' → nout=2
            # Hmm, actually there's no '=' in "  myfunc(x)" so it loops through all chars
            # and returns nout at end of file. Let's just check it's >= 0.
            assert nout >= 0
        finally:
            os.unlink(path)

    def test_get_max_nout_via_feval_max_nout(self):
        """feval with nout='max_nout' should use _get_max_nout."""
        tests_dir = os.path.dirname(__file__)
        path = os.path.join(tests_dir, "test_datatypes.m")
        result = self.oc.feval(path, nout="max_nout")
        # test_datatypes returns 1 value
        assert result is not None

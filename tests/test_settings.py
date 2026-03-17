"""Tests for Oct2PySettings and configure()."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

import oct2py
from oct2py import Oct2Py, Oct2PySettings


class TestOct2PySettings:
    """Tests for Oct2PySettings field defaults, env var resolution, and aliases."""

    def test_defaults(self):
        """All fields have the expected defaults when no env vars are set."""
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith("OCT2PY_") and k not in ("OCTAVE_EXECUTABLE", "OCTAVE")
        }
        with patch.dict(os.environ, env, clear=True):
            s = Oct2PySettings()
        assert s.executable is None
        assert s.timeout is None
        assert s.oned_as == "row"
        assert s.temp_dir is None
        assert s.convert_to_float is True
        assert s.backend == "default"
        assert s.keep_matlab_shapes is False
        assert s.auto_show is None
        assert s.plot_format == "svg"
        assert s.plot_name == "plot"
        assert s.plot_width is None
        assert s.plot_height is None
        assert s.plot_res is None
        assert s.extra_cli_options == ""

    # --- OCT2PY_* env vars ---

    def test_oct2py_timeout_env_var(self):
        """OCT2PY_TIMEOUT sets the timeout field."""
        with patch.dict(os.environ, {"OCT2PY_TIMEOUT": "60"}):
            s = Oct2PySettings()
        assert s.timeout == 60.0

    def test_oct2py_backend_env_var(self):
        """OCT2PY_BACKEND sets the backend field."""
        with patch.dict(os.environ, {"OCT2PY_BACKEND": "qt"}):
            s = Oct2PySettings()
        assert s.backend == "qt"

    def test_oct2py_oned_as_env_var(self):
        """OCT2PY_ONED_AS sets the oned_as field."""
        with patch.dict(os.environ, {"OCT2PY_ONED_AS": "column"}):
            s = Oct2PySettings()
        assert s.oned_as == "column"

    def test_oct2py_convert_to_float_env_var(self):
        """OCT2PY_CONVERT_TO_FLOAT=false disables float conversion."""
        with patch.dict(os.environ, {"OCT2PY_CONVERT_TO_FLOAT": "false"}):
            s = Oct2PySettings()
        assert s.convert_to_float is False

    def test_oct2py_extra_cli_options_env_var(self):
        """OCT2PY_EXTRA_CLI_OPTIONS sets the extra_cli_options field."""
        with patch.dict(os.environ, {"OCT2PY_EXTRA_CLI_OPTIONS": "--traditional"}):
            s = Oct2PySettings()
        assert s.extra_cli_options == "--traditional"

    # --- executable aliases ---

    def test_octave_executable_env_var(self):
        """OCTAVE_EXECUTABLE sets the executable field."""
        env = {k: v for k, v in os.environ.items() if k != "OCTAVE"}
        env["OCTAVE_EXECUTABLE"] = "/env/octave"
        with patch.dict(os.environ, env, clear=True):
            s = Oct2PySettings()
        assert s.executable == "/env/octave"

    def test_octave_env_var_alias(self):
        """OCTAVE sets the executable field when OCTAVE_EXECUTABLE is absent."""
        env = {k: v for k, v in os.environ.items() if k != "OCTAVE_EXECUTABLE"}
        env["OCTAVE"] = "/alias/octave"
        with patch.dict(os.environ, env, clear=True):
            s = Oct2PySettings()
        assert s.executable == "/alias/octave"

    def test_octave_executable_takes_precedence_over_octave(self):
        """OCTAVE_EXECUTABLE takes precedence over OCTAVE."""
        with patch.dict(
            os.environ, {"OCTAVE_EXECUTABLE": "/primary/octave", "OCTAVE": "/fallback/octave"}
        ):
            s = Oct2PySettings()
        assert s.executable == "/primary/octave"

    # --- programmatic construction ---

    def test_oct2py_load_octaverc_env_var(self):
        """OCT2PY_LOAD_OCTAVERC=false disables octaverc loading."""
        with patch.dict(os.environ, {"OCT2PY_LOAD_OCTAVERC": "false"}):
            s = Oct2PySettings()
        assert s.load_octaverc is False

    def test_oct2py_plot_format_env_var(self):
        """OCT2PY_PLOT_FORMAT sets the plot_format field."""
        with patch.dict(os.environ, {"OCT2PY_PLOT_FORMAT": "png"}):
            s = Oct2PySettings()
        assert s.plot_format == "png"

    def test_oct2py_plot_width_env_var(self):
        """OCT2PY_PLOT_WIDTH sets the plot_width field."""
        with patch.dict(os.environ, {"OCT2PY_PLOT_WIDTH": "1280"}):
            s = Oct2PySettings()
        assert s.plot_width == 1280

    def test_programmatic_values(self):
        """Fields can be set directly when constructing the settings object."""
        s = Oct2PySettings(
            executable="/prog/octave",
            timeout=15.0,
            backend="disable",
            oned_as="column",
            extra_cli_options="--traditional",
            plot_format="png",
            plot_name="fig",
            plot_width=800,
            plot_height=600,
            plot_res=150,
        )
        assert s.executable == "/prog/octave"
        assert s.timeout == 15.0
        assert s.backend == "disable"
        assert s.oned_as == "column"
        assert s.extra_cli_options == "--traditional"
        assert s.plot_format == "png"
        assert s.plot_name == "fig"
        assert s.plot_width == 800
        assert s.plot_height == 600
        assert s.plot_res == 150


@pytest.fixture()
def restore_octave():
    """Save and restore oct2py.octave after each configure test.

    Also mocks exit() on the saved instance so the real Octave session is
    never closed by configure() during a test.
    """
    saved = oct2py.octave
    with patch.object(saved, "exit"):
        yield
    # Null out the engine of whatever configure() installed, then restore.
    if oct2py.octave is not saved:
        oct2py.octave._engine = None
    oct2py.octave = saved


class TestConfigure:
    """Tests for the oct2py.configure() function."""

    def _make_fake_engine(self, executable="/resolved/octave"):
        fake = MagicMock()
        fake.tmp_dir = tempfile.mkdtemp()
        fake.executable = executable
        return fake

    def test_configure_with_kwargs_builds_settings(self, restore_octave):
        """configure(**kwargs) builds an Oct2PySettings from kwargs."""
        fake = self._make_fake_engine()
        original = oct2py.octave
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oct2py.configure(backend="disable", timeout=42)
        new_instance = oct2py.octave
        assert new_instance is not original
        assert new_instance.settings.backend == "disable"
        assert new_instance.settings.timeout == 42

    def test_configure_with_settings_object(self, restore_octave):
        """configure(settings=s) uses the provided settings object directly."""
        s = Oct2PySettings(backend="disable", timeout=99, oned_as="column")
        fake = self._make_fake_engine()
        original = oct2py.octave
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oct2py.configure(settings=s)
        new_instance = oct2py.octave
        assert new_instance is not original
        assert new_instance.settings.backend == "disable"
        assert new_instance.settings.timeout == 99
        assert new_instance.settings.oned_as == "column"

    def test_configure_no_args_uses_defaults(self, restore_octave):
        """configure() with no args creates a default-settings instance."""
        fake = self._make_fake_engine()
        original = oct2py.octave
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oct2py.configure()
        new_instance = oct2py.octave
        assert new_instance is not original
        assert isinstance(new_instance.settings, Oct2PySettings)
        assert new_instance.settings.backend == "default"

    def test_configure_replaces_global_octave(self, restore_octave):
        """configure() replaces oct2py.octave with a new Oct2Py instance."""
        fake = self._make_fake_engine()
        before = oct2py.octave
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oct2py.configure(backend="disable")
        assert oct2py.octave is not before
        assert isinstance(oct2py.octave, Oct2Py)

    def test_configure_exits_old_instance(self):
        """configure() calls exit() on the previous global octave instance."""
        fake = self._make_fake_engine()
        old_instance = MagicMock()
        # patch.object restores oct2py.octave on exit, so the real session is unaffected.
        with (
            patch.object(oct2py, "octave", old_instance),
            patch("oct2py.core.OctaveEngine", return_value=fake),
        ):
            oct2py.configure(backend="disable")
        old_instance.exit.assert_called_once()

    def test_configure_kwargs_override_env_vars(self, restore_octave):
        """kwargs passed to configure() take precedence over OCT2PY_* env vars."""
        fake = self._make_fake_engine()
        with (
            patch.dict(os.environ, {"OCT2PY_BACKEND": "qt"}),
            patch("oct2py.core.OctaveEngine", return_value=fake),
        ):
            oct2py.configure(backend="disable")
        assert oct2py.octave.settings.backend == "disable"

    def test_configure_settings_ignored_if_kwargs_provided(self, restore_octave):
        """When both settings and kwargs are passed, settings wins (kwargs are ignored)."""
        # The function signature is configure(settings=None, **kwargs).
        # If a pre-built settings object is passed, kwargs are silently ignored
        # because Oct2PySettings(**kwargs) is only called when settings is None.
        s = Oct2PySettings(backend="disable")
        fake = self._make_fake_engine()
        with patch("oct2py.core.OctaveEngine", return_value=fake):
            oct2py.configure(settings=s, timeout=77)
        # timeout=77 is not applied — it was passed as a kwarg but settings was provided.
        # The instance settings are derived from s, so backend is preserved.
        assert oct2py.octave.settings.backend == "disable"
        assert oct2py.octave.settings.timeout != 77

"""Tests for Oct2PySettings."""

import os
from unittest.mock import patch

import pytest

from oct2py import Oct2PySettings


class TestOct2PySettings:
    """Tests for Oct2PySettings field defaults, env var resolution, and aliases."""

    def test_defaults(self):
        """All fields have the expected defaults when no env vars are set."""
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("OCT2PY_") and k not in ("OCTAVE_EXECUTABLE", "OCTAVE")}
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
        with patch.dict(os.environ, {"OCTAVE_EXECUTABLE": "/primary/octave",
                                     "OCTAVE": "/fallback/octave"}):
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

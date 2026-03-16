"""Tests for oct2py IPython magic integration."""

import os
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("IPython")

from IPython.core.interactiveshell import InteractiveShell
from traitlets.config import Config

from oct2py.ipython.octavemagic import OctaveMagics


@pytest.fixture
def ip():
    shell = MagicMock(spec=InteractiveShell)
    shell.user_ns = {}
    shell.push.side_effect = shell.user_ns.update
    shell.config = Config()
    return shell


@pytest.fixture
def magics(ip, tmp_path):
    with patch("oct2py.ipython.octavemagic.oct2py") as mock_oct2py_module:
        mock_oct2py_module.octave = MagicMock()
        m = OctaveMagics(ip)
    mock_oct = MagicMock()
    mock_oct.temp_dir = str(tmp_path)
    mock_oct.eval.return_value = 42
    mock_oct.extract_figures.return_value = []
    m._oct = mock_oct
    m._display = MagicMock()
    return m


def test_executable_trait_sets_oct2py(ip):
    """Setting the executable trait creates a new Oct2Py session with OCTAVE_EXECUTABLE set."""
    orig = os.environ.pop("OCTAVE_EXECUTABLE", None)
    try:
        with patch("oct2py.ipython.octavemagic.oct2py") as mock_oct2py_module:
            mock_oct2py_module.octave = MagicMock()
            new_session = MagicMock()
            mock_oct2py_module.Oct2Py.return_value = new_session

            magics = OctaveMagics(ip)
            magics.executable = "/usr/bin/octave-custom"

            assert os.environ.get("OCTAVE_EXECUTABLE") == "/usr/bin/octave-custom"
            mock_oct2py_module.Oct2Py.assert_called_once_with()
            assert magics._oct is new_session
    finally:
        if orig is None:
            os.environ.pop("OCTAVE_EXECUTABLE", None)
        else:
            os.environ["OCTAVE_EXECUTABLE"] = orig


def test_octave_line_magic_returns_value(magics):
    """Line magic (cell=None) returns the eval result."""
    result = magics.octave("X = 1", cell=None, local_ns={})
    assert result == 42
    magics._oct.eval.assert_called_once()


def test_octave_cell_magic_returns_none(magics):
    """Cell magic (cell provided) returns None regardless of eval result."""
    result = magics.octave("", cell="X = 1\n", local_ns={})
    assert result is None
    magics._oct.eval.assert_called_once()


def test_octave_local_ns_none_defaults_to_empty(magics):
    """When local_ns is None it defaults to {} without error."""
    result = magics.octave("X = 1", cell=None, local_ns=None)
    assert result == 42


def test_octave_input_from_local_ns(magics):
    """Variables in local_ns are pushed to Octave when -i is used."""
    magics.octave("-i myvar mean(myvar)", cell=None, local_ns={"myvar": 99})
    magics._oct.push.assert_called_with("myvar", 99)


def test_octave_input_from_shell_ns(magics, ip):
    """Variables absent from local_ns fall back to shell.user_ns."""
    ip.user_ns["shellvar"] = 77
    magics.octave("-i shellvar mean(shellvar)", cell=None, local_ns={})
    magics._oct.push.assert_called_with("shellvar", 77)


def test_octave_size_arg_sets_width_height(magics):
    """The -s flag parses width,height for plot sizing."""
    magics.octave("-s 640,480 X = 1", cell=None, local_ns={})
    kwargs = magics._oct.eval.call_args.kwargs
    assert kwargs["plot_width"] == 640
    assert kwargs["plot_height"] == 480


def test_octave_width_height_args(magics):
    """The -w and -h flags set plot dimensions directly."""
    magics.octave("-w 320 -h 240 X = 1", cell=None, local_ns={})
    kwargs = magics._oct.eval.call_args.kwargs
    assert kwargs["plot_width"] == 320
    assert kwargs["plot_height"] == 240


def test_octave_temp_dir_valid(magics):
    """A valid --temp_dir is forwarded to eval."""
    valid_dir = magics._oct.temp_dir
    magics.octave(f"--temp_dir {valid_dir} X = 1", cell=None, local_ns={})
    kwargs = magics._oct.eval.call_args.kwargs
    assert kwargs["temp_dir"] == valid_dir


def test_octave_temp_dir_invalid_falls_back(magics):
    """An invalid --temp_dir path falls back to _oct.temp_dir."""
    magics.octave("--temp_dir /nonexistent/path/xyz X = 1", cell=None, local_ns={})
    kwargs = magics._oct.eval.call_args.kwargs
    assert kwargs["temp_dir"] == magics._oct.temp_dir


def test_octave_plot_dir_existing_is_removed(magics):
    """If plot_dir already exists it is cleared before re-creation."""
    plot_dir = os.path.join(magics._oct.temp_dir, "plots")
    os.makedirs(plot_dir)
    sentinel = os.path.join(plot_dir, "old_file.png")
    open(sentinel, "w").close()
    magics.octave("X = 1", cell=None, local_ns={})
    assert not os.path.exists(sentinel)
    assert os.path.isdir(plot_dir)


def test_octave_output_pulled_to_shell(magics, ip):
    """Variables specified with -o are pulled from Octave and pushed to the shell namespace."""
    magics._oct.pull.return_value = 123
    magics.octave("-o result result = 42", cell=None, local_ns={})
    magics._oct.pull.assert_called_with("result")
    assert ip.user_ns["result"] == 123


def test_octave_figures_displayed(magics):
    """Images returned by extract_figures are forwarded to display."""
    img = MagicMock()
    magics._oct.extract_figures.return_value = [img]
    magics.octave("plot([1 2 3])", cell=None, local_ns={})
    magics._display.assert_called_once_with(img)

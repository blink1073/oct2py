"""Tests for oct2py IPython magic integration."""

import os
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("IPython")

from IPython.core.interactiveshell import InteractiveShell

from oct2py.ipython.octavemagic import OctaveMagics


@pytest.fixture(scope="module")
def ip():
    return InteractiveShell.instance()


def test_executable_trait_sets_oct2py(ip, monkeypatch):
    """Setting the executable trait creates a new Oct2Py session with OCTAVE_EXECUTABLE set."""
    with patch("oct2py.ipython.octavemagic.oct2py") as mock_oct2py_module:
        mock_oct2py_module.octave = MagicMock()
        new_session = MagicMock()
        mock_oct2py_module.Oct2Py.return_value = new_session

        magics = OctaveMagics(ip)
        magics.executable = "/usr/bin/octave-custom"

        assert os.environ.get("OCTAVE_EXECUTABLE") == "/usr/bin/octave-custom"
        mock_oct2py_module.Oct2Py.assert_called_once_with()
        assert magics._oct is new_session

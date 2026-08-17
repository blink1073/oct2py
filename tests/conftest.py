"""Shared pytest configuration for the oct2py test suite."""

import os
import shutil
import sys

import pytest

# `octave` launches the Qt-linked GUI binary even with --no-gui: slower to
# start, and on a cold Windows runner it has stalled past pexpect's 30s wait
# for the first prompt. Linux keeps it, since octave-cli is built without the
# GUI libraries and inline plotting fails without the qt graphics toolkit.
#
# Set at import time, before the test modules import oct2py: that import builds
# the module-level session, one per xdist worker, for the whole run.
_OCTAVE_CLI = None if sys.platform.startswith("linux") else shutil.which("octave-cli")

# True when this suite owns the value: unset, or already the path set here in
# the parent, which xdist workers inherit. Anything else is a deliberate choice
# from the environment and wins; the flatpak and snap CI jobs rely on that.
_APPLIED = bool(_OCTAVE_CLI) and os.environ.get("OCTAVE_EXECUTABLE") in (None, _OCTAVE_CLI)
if _APPLIED:
    os.environ["OCTAVE_EXECUTABLE"] = _OCTAVE_CLI  # type:ignore[assignment]


@pytest.fixture(scope="session")
def gui_octave():
    """A session on the GUI-linked `octave`, for tests that render figures.

    Shared, so leave the workspace as you found it and do not exit it.  An
    empty executable leaves oct2py to resolve one as it normally would, which
    is what the flatpak and snap jobs need.
    """
    from oct2py import Oct2Py

    # Deliberately not offscreen: these tests render figures to files, and
    # QT_QPA_PLATFORM=offscreen makes Octave write an empty image.  A test that
    # opens a real figure window needs the opposite and builds its own session.
    oc = Oct2Py(executable=shutil.which("octave") or "")
    yield oc
    oc.exit()


@pytest.fixture(autouse=True)
def _octave_executable(request, monkeypatch):
    """Hand the GUI-linked `octave` back to a test that cannot ask for it.

    For tests whose session is built out of reach, so `gui_octave` cannot be
    used.  Only covers sessions created during the test: class fixtures run
    first, so a ``setup_class`` session still gets octave-cli.
    """
    if _APPLIED and request.node.get_closest_marker("needs_octave_gui"):
        monkeypatch.delenv("OCTAVE_EXECUTABLE", raising=False)

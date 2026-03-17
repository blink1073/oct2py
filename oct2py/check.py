"""oct2py system and dependency check."""
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

from __future__ import annotations

import os
import platform
import shutil
import sys
from importlib.metadata import version

from ._version import __version__


def check() -> None:
    """Print system and dependency information for oct2py.

    Displays Python environment details, oct2py and dependency versions,
    Octave executable location, and a live connection test including
    Octave version and available graphics toolkits.

    Examples
    --------
    >>> from oct2py.check import check
    >>> check()  # doctest: +SKIP

    """
    print(f"Platform:     {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python:       {sys.version}")
    print(f"Python path:  {sys.executable}")
    print()
    print(f"oct2py:       {__version__}")
    print(f"numpy:        {version('numpy')}")
    print(f"scipy:        {version('scipy')}")
    print(f"octave_kernel:{version('octave_kernel')}")
    print()

    executable = (
        os.environ.get("OCTAVE_EXECUTABLE") or shutil.which("octave-cli") or shutil.which("octave")
    )
    print(f"Octave exe:   {executable or '(not found)'}")
    print()

    print("Connecting to Octave...")
    try:
        from .core import Oct2Py  # noqa: PLC0415

        oc = Oct2Py()
        octave_ver = oc.eval("version", verbose=False)
        print(f"Octave:       {octave_ver}")
        toolkit = oc.eval("graphics_toolkit", verbose=False)
        toolkits = oc.eval("available_graphics_toolkits", verbose=False)
        toolkits_str = (
            ", ".join(str(t) for t in toolkits.flat) if hasattr(toolkits, "flat") else str(toolkits)
        )
        print(f"Graphics:     {toolkit} (available: {toolkits_str})")
        oc.exit()
        print("Connection OK")
    except Exception as e:  # pragma: no cover
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    check()

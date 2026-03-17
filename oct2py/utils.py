"""oct2py general utils."""
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

import logging
import os


class Oct2PyError(Exception):
    """Called when we can't open Octave or Octave throws an error"""

    pass


class Oct2PyWarning(UserWarning):
    """Warning raised by oct2py for deprecations and other advisory conditions."""

    pass


def get_log(name=None):
    """Return a logger for oct2py.

    Output may be sent to the logger using the `debug`, `info`, `warning`,
    `error` and `critical` methods.

    Parameters
    ----------
    name : str
        Name of the log.

    Returns
    -------
    log : object
        The logger object.
    """
    name = "oct2py" if name is None else "oct2py." + name
    return logging.getLogger(name)


def _augment_path_for_windows(executable: str) -> None:
    """On Windows, prepend Octave's bundled MinGW/MSYS tool dirs to PATH.

    The Octave GUI launcher adds <install>/mingw64/bin and <install>/usr/bin
    to PATH before starting octave-cli, providing Unix commands like ``cat``.
    When oct2py spawns octave-cli directly those directories are missing.
    This function detects them from the resolved executable path and prepends
    them so the subprocess inherits the same environment.
    """
    if os.name != "nt":
        return

    if not executable:
        return

    executable = os.path.realpath(executable)
    exe_dir = os.path.dirname(executable)
    # Standard installer: <root>/mingw64/bin/octave-cli.exe  → root = grandparent
    # Portable layout:    <root>/bin/octave-cli.exe          → root = parent
    parent = os.path.dirname(exe_dir)
    grandparent = os.path.dirname(parent)

    current_path = os.environ.get("PATH", "")
    lower_set = {p.lower() for p in current_path.split(os.pathsep)}
    new_entries: list[str] = []

    for root in (grandparent, parent):
        for sub in (os.path.join("mingw64", "bin"), os.path.join("usr", "bin")):
            tool_dir = os.path.join(root, sub)
            if os.path.isdir(tool_dir) and tool_dir.lower() not in lower_set:
                new_entries.append(tool_dir)
                lower_set.add(tool_dir.lower())

    if new_entries:
        os.environ["PATH"] = os.pathsep.join(new_entries) + os.pathsep + current_path

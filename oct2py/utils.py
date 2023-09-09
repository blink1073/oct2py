"""oct2py general utils."""
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

import logging
import sys


class Oct2PyError(Exception):
    """Called when we can't open Octave or Octave throws an error"""

    pass


def get_log(name=None):
    """Return a console logger.

    Output may be sent to the logger using the `debug`, `info`, `warning`,
    `error` and `critical` methods.

    Parameters
    ----------
    name : str
        Name of the log.
    """
    name = "oct2py" if name is None else "oct2py." + name

    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    return log


def _setup_log():
    """Configure root logger."""
    try:
        handler = logging.StreamHandler(stream=sys.stdout)
    except TypeError:  # pragma: no cover
        handler = logging.StreamHandler(strm=sys.stdout)  # type:ignore[call-overload]

    log = get_log()
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False


_setup_log()

"""oct2py general utils."""
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

import logging


class Oct2PyError(Exception):
    """Called when we can't open Octave or Octave throws an error"""

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


# Add a NullHandler so that log records are silently discarded unless the
# application configures logging.  Per Python logging best practices, libraries
# must not install their own handlers or set levels on their loggers.
logging.getLogger("oct2py").addHandler(logging.NullHandler())

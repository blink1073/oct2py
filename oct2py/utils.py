# -*- coding: utf-8 -*-
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

from __future__ import absolute_import, print_function, division

import inspect
import dis
import logging
import sys


from .compat import PY2


class Oct2PyError(Exception):
    """ Called when we can't open Octave or Octave throws an error
    """
    pass


def get_log(name=None):
    """Return a console logger.

    Output may be sent to the logger using the `debug`, `info`, `warning`,
    `error` and `critical` methods.

    Parameters
    ----------
    name : str
        Name of the log.

    References
    ----------
    .. [1] Logging facility for Python,
           http://docs.python.org/library/logging.html

    """
    if name is None:
        name = 'oct2py'
    else:
        name = 'oct2py.' + name

    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    return log


def _setup_log():
    """Configure root logger.
    """
    try:
        handler = logging.StreamHandler(stream=sys.stdout)
    except TypeError:  # pragma: no cover
        handler = logging.StreamHandler(strm=sys.stdout)

    log = get_log()
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False


_setup_log()

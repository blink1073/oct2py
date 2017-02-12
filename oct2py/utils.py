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


def get_nout():
    """
    Return the number of return values the caller is expecting.

    Adapted from the ompc project.

    Returns
    =======
    out : int
        Number of arguments expected by caller.

    """
    frame = inspect.currentframe()
    # step into the function that called us
    # nout is two frames back
    frame = frame.f_back.f_back
    bytecode = frame.f_code.co_code
    if(sys.version_info >= (3, 6)):
        instruction = bytecode[frame.f_lasti + 2]
    else:
        instruction = bytecode[frame.f_lasti + 3]
    instruction = ord(instruction) if PY2 else instruction
    if instruction == dis.opmap['UNPACK_SEQUENCE']:
        if(sys.version_info >= (3, 6)):
            howmany = bytecode[frame.f_lasti + 3]
        else:
            howmany = bytecode[frame.f_lasti + 4]
        howmany = ord(howmany) if PY2 else howmany
        return howmany
    elif instruction in [dis.opmap['POP_TOP'], dis.opmap['PRINT_EXPR']]:
        return 0
    return 1


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

# -*- coding: utf-8 -*-
import sys

PY2 = sys.version[0] == '2'
PY3 = sys.version[0] == '3'


if PY2:
    unicode = unicode
    long = long
    from StringIO import StringIO
    import Queue as queue
    input = raw_input
else:  # pragma : no cover
    input = input
    unicode = str
    long = int
    from io import StringIO
    import queue

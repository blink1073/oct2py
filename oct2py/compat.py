# -*- coding: utf-8 -*-
import sys

PY2 = sys.version[0] == '2'
PY3 = sys.version[0] == '3'


if not PY2:  # pragma : no cover
    unicode = str
    long = int
    basestring = str
else:  # pragma : no cover
    unicode = unicode
    long = long
    basestring = basestring
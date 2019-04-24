# -*- coding: utf-8 -*-
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

from __future__ import print_function, absolute_import
import time
from .compat import PY2


def demo(delay=1, interactive=True):
    """
    Play a demo script showing most of the oct2py api features.

    Parameters
    ==========
    delay : float
        Time between each command in seconds.

    """
    script = """
    #########################
    # Oct2Py demo
    #########################
    import numpy as np
    from oct2py import Oct2Py
    oc = Oct2Py()
    # basic commands
    print(oc.abs(-1))
    print(oc.upper('xyz'))
    # plotting
    oc.plot([1,2,3],'-o', 'linewidth', 2)
    raw_input('Press Enter to continue...')
    oc.close()
    xx = np.arange(-2*np.pi, 2*np.pi, 0.2)
    oc.surf(np.subtract.outer(np.sin(xx), np.cos(xx)))
    raw_input('Press Enter to continue...')
    oc.close()
    # getting help
    help(oc.svd)
    # single vs. multiple return values
    print(oc.svd(np.array([[1,2], [1,3]])))
    U, S, V = oc.svd([[1,2], [1,3]], nout=3)
    print(U, S, V)
    # low level constructs
    oc.eval("y=ones(3,3)")
    print(oc.pull("y"))
    oc.eval("x=zeros(3,3)", verbose=True)
    t = oc.eval('rand(1, 2)', verbose=True)
    y = np.zeros((3,3))
    oc.push('y', y)
    print(oc.pull('y'))
    from oct2py import Struct
    y = Struct()
    y.b = 'spam'
    y.c.d = 'eggs'
    print(y.c['d'])
    print(y)
    #########################
    # Demo Complete!
    #########################
    """
    if not PY2:
        script = script.replace('raw_input', 'input')

    for line in script.strip().split('\n'):
        line = line.strip()
        if not 'input(' in line:
            time.sleep(delay)
            print(">>> {0}".format(line))
            time.sleep(delay)
        if not interactive:
            if 'plot' in line or 'surf' in line or 'input(' in line:
                line = 'print()'
        exec(line)

if __name__ == '__main__':  # pragma: no cover
    demo(delay=0.25)

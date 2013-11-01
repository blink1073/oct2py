"""
.. module:: demo
   :synopsis: Play a demo script showing most of the p2oct api features.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import print_function
import time
from .compat import PY2


def demo(delay=2, interactive=True):
    """
    Play a demo script showing most of the oct2py api features.

    Parameters
    ==========
    delay : float
        Time between each command in seconds.

    """
    script = """
    import numpy as np
    from oct2py import Oct2Py
    oc = Oct2Py()
    # basic commands
    print(oc.abs(-1))
    print(oc.upper('xyz'))
    # plotting
    oc.plot([1,2,3],'-o')
    raw_input('Press Enter to continue...')
    xx = np.arange(-2*np.pi, 2*np.pi, 0.2)
    oc.surf(np.subtract.outer(np.sin(xx), np.cos(xx)))
    raw_input('Press Enter to continue...')
    # getting help
    help(oc.svd)
    # single vs. multiple return values
    print(oc.svd(np.array([[1,2], [1,3]])))
    U, S, V = oc.svd([[1,2], [1,3]])
    print(U, S, V)
    # low level constructs
    oc.run("y=ones(3,3)")
    print(oc.get("y"))
    oc.run("x=zeros(3,3)", verbose=True)
    x = oc.call('rand', 1, 4)
    print(x)
    t = oc.call('rand', 1, 2, verbose=True)
    y = np.zeros((3,3))
    oc.put('y', y)
    print(oc.get('y'))
    from oct2py import Struct
    y = Struct()
    y.b = 'spam'
    y.c.d = 'eggs'
    print(y.c['d'])
    print(y)
    """
    if not PY2:
        script = script.replace('raw_input', 'input')

    print('oct2py demo')
    print('*' * 20)
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
    time.sleep(delay)
    print('*' * 20)
    print('DEMO COMPLETE!')

if __name__ == '__main__':  # pragma: no cover
    demo(delay=0.5)

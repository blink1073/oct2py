""" py2oct_demo -  Play a demo script showing most of the p2oct api features
"""
import time


def demo(delay=2):
    """ Play a demo script showing most of the p2oct api features """
    script = """
    import numpy as np
    from py2oct import Octave
    oc = Octave()
    # basic commands
    print oc.abs(-1)
    print oc.upper('xyz')
    # plotting
    oc.plot([1,2,3],'-o')
    raw_input('Press Enter to continue...')
    xx = np.arange(-2*np.pi, 2*np.pi, 0.2)
    oc.surf(np.subtract.outer(np.sin(xx), np.cos(xx)))
    raw_input('Press Enter to continue...')
    # getting help
    oc.lookfor('singular value')
    help(oc.svd)
    # single vs. multiple return values
    print oc.svd(np.array([[1,2], [1,3]]))
    U, S, V = oc.svd([[1,2], [1,3]])
    print U, S, V
    # low level constructs
    oc.run("y=ones(3,3)")
    print oc.get("y")
    oc.run("x=zeros(3,3)", verbose=True)
    x = oc.call('rand', 1, 4)
    print x
    t = oc.call('rand', 1, 2, verbose=True)
    y = np.zeros((3,3))
    oc.put('y', y)
    print oc.get('y')
    from py2oct import OctaveStruct
    y = OctaveStruct()
    y.b = 'foo'
    y.c.d = 'bar'
    print y['b']
    print y
    """

    print 'py2oct demo'
    print '*' * 20
    for line in script.strip().split('\n'):
        line = line.strip()
        if not line.startswith('raw_input'):
            time.sleep(delay)
            print ">>>", line
            time.sleep(delay)
        exec(line)
    time.sleep(delay)
    print '*' * 20
    print 'DEMO COMPLETE!'

if __name__ == '__main__':
    demo(delay=2)

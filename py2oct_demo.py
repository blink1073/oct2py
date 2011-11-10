from py2oct import Octave
import time
import numpy as np

def demo(delay):
    print '*' * 20
    print ">>> from py2oct import Octave"
    time.sleep(delay)
    print ">>> oc = Octave()"
    oc = Octave()
    time.sleep(delay)
    print ">>> oc.plot([1,2,3],'-o')"
    time.sleep(delay)
    oc.plot([1,2,3], '-o')
    raw_input('Press Enter to continue...')
    print ">>> from numpy import *"
    time.sleep(delay)
    print ">>> xx = arange(-2*pi, 2*pi, 0.2)"
    time.sleep(delay)
    print ">>> oc.surf(subtract.outer(sin(xx), cos(xx)))"
    time.sleep(delay)
    xx = np.arange(-2*np.pi, 2*np.pi, 0.2)
    oc.surf(np.subtract.outer(np.sin(xx),np.cos(xx)))
    raw_input('Press Enter to continue...')
    print ">>> oc.lookfor('singular value')"
    time.sleep(delay)
    oc.lookfor('singular value')
    time.sleep(delay)
    print ">>> help(oc.svd)"
    time.sleep(delay)
    help(oc.svd)
    time.sleep(delay)
    print ">>> print oc.svd(array([[1,2], [1,3]]))"
    time.sleep(delay)
    print oc.svd(np.array([[1,2], [1,3]]))
    time.sleep(delay)
    print ">>> U, S, V = oc.svd([[1,2], [1,3]])"
    time.sleep(delay)
    print ">>> print U, S, V"
    time.sleep(delay)
    U, S, V = oc.svd([[1,2], [1,3]])
    print U, S, V
    time.sleep(delay)
    print ">>> print oc.abs(-1)"
    time.sleep(delay)
    print oc.abs(-1)
    time.sleep(delay)
    print ">>> print oc.upper('abcde')"
    time.sleep(delay)
    print oc.upper('abcde')
    time.sleep(delay)
    print ">>> print oc.log(0.)"
    time.sleep(delay)
    print oc.log(0.)
    time.sleep(delay)
    print '*' * 20
    print 'DEMO COMPLETE!'
    
if __name__ == '__main__':
    demo(delay=3)
    
from py2oct import Octave
import time
import timeit
import numpy as np

    
def raw_overhead():
    """ Run a fast matlab command and see how long it takes """
    oc.run("x = 1")
    
def large_array_put():
    """ Create a large matrix and load it into the octave session """
    oc.put('a', a)

def large_array_get():
    """ Retrieve the large matrix "x" from the octave session """
    oc.get('a')
        
if __name__ == '__main__':
    
    print 'py2oct speed test'
    print '*' * 20
    
    oc = Octave()
    time.sleep(1) 
    a = np.reshape(np.arange(100000),(-1,))
    
    print 'raw_overhead: ',
    t = timeit.timeit(raw_overhead, number=200) / 200
    print '%d usec per loop' % (t * 1e6)
    
    print 'large array put: ',
    t = timeit.timeit(large_array_put, number=200) / 200
    print '%0.1f msec per loop' % (t * 1e3)
    
    print 'large array get: ',
    t = timeit.timeit(large_array_get, number=200) / 200
    print '%0.1f msec per loop' % (t * 1e3)
    
    
import time

def demo(delay):
    """ Play a demo script showing most of the api features """
    script = """
    from py2oct import Octave
    oc = Octave()
    oc.plot([1,2,3],'-o')
    raw_input('Press Enter to continue...')
    import numpy as np
    xx = np.arange(-2*np.pi, 2*np.pi, 0.2)
    oc.surf(np.subtract.outer(np.sin(xx), np.cos(xx)))
    raw_input('Press Enter to continue...')
    oc.lookfor('singular value')
    help(oc.svd)
    print oc.svd(np.array([[1,2], [1,3]]))
    U, S, V = oc.svd([[1,2], [1,3]])
    print U, S, V
    print oc.abs(-1)
    print oc.upper('abcde')
    print oc.log(0.)
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
    
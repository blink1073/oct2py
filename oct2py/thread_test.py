""" py2oct_thread - Test Starting Multiple Threads

Verify that they each have their own session
"""
import threading
import datetime
from oct2py import Oct2Py


class ThreadClass(threading.Thread):
    """ Octave instance thread """

    def run(self):
        """ Create a unique instance of Octave and verify namespace uniqueness
        """
        octave = Oct2Py()
        # write the same variable name in each thread and read it back
        octave.put('name', self.getName())
        name = octave.get('name')
        now = datetime.datetime.now()
        print "%s got '%s' at %s" % (self.getName(), name, now)
        octave._close()
        assert self.getName() == name
        return


def thread_test(nthreads=3):
    """ Start a number of threads and verify each has a unique Octave session

    Input : nthreads (int) - the number of threads to use
    """
    print "Starting %s threads at %s" % (nthreads, datetime.datetime.now())
    threads = []
    for i in range(nthreads):
        t = ThreadClass()
        t.setDaemon(True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    print 'All threads closed at %s' % datetime.datetime.now()


if __name__ == '__main__':
    thread_test()

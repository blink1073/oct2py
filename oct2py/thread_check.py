"""
.. module:: thread_test
   :synopsis: Test Starting Multiple Threads.
              Verify that they each have their own session

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import print_function
import threading
import datetime
from .session import Oct2Py, Oct2PyError


class ThreadClass(threading.Thread):
    """Octave instance thread
    """

    def run(self):
        """
        Create a unique instance of Octave and verify namespace uniqueness.

        Raises
        ======
        Oct2PyError
            If the thread does not sucessfully demonstrate independence

        """
        octave = Oct2Py()
        # write the same variable name in each thread and read it back
        octave.put('name', self.getName())
        name = octave.get('name')
        now = datetime.datetime.now()
        print("{0} got '{1}' at {2}".format(self.getName(), name, now))
        octave.close()
        try:
            assert self.getName() == name
        except AssertionError:  # pragma: no cover
            raise Oct2PyError('Thread collision detected')
        return


def thread_test(nthreads=3):
    """
    Start a number of threads and verify each has a unique Octave session.

    Parameters
    ==========
    nthreads : int
        Number of threads to use.

    Raises
    ======
    Oct2PyError
        If the thread does not sucessfully demonstrate independence.

    """
    print("Starting {0} threads at {1}".format(nthreads,
                                               datetime.datetime.now()))
    threads = []
    for i in range(nthreads):
        thread = ThreadClass()
        thread.setDaemon(True)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    print('All threads closed at {0}'.format(datetime.datetime.now()))


if __name__ == '__main__':  # pragma: no cover
    thread_test()

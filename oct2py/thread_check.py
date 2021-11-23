# -*- coding: utf-8 -*-
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

from __future__ import print_function, absolute_import
import threading
import datetime
from . import Oct2Py, Oct2PyError


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
        octave.push('name', self.name)
        name = octave.pull('name')
        now = datetime.datetime.now()
        print("{0} got '{1}' at {2}".format(self.name, name, now))
        octave.exit()
        try:
            assert self.name == name
        except AssertionError:  # pragma: no cover
            raise Oct2PyError('Thread collision detected')
        return


def thread_check(nthreads=3):
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
        thread.daemon = True
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    print('All threads closed at {0}'.format(datetime.datetime.now()))


if __name__ == '__main__':  # pragma: no cover
    thread_check()

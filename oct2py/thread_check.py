# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.


import datetime
import threading

from . import Oct2Py, Oct2PyError


class ThreadClass(threading.Thread):
    """Octave instance thread"""

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
        octave.push("name", self.name)
        name = octave.pull("name")
        now = datetime.datetime.now()
        print(f"{self.name} got '{name}' at {now}")
        octave.exit()
        try:
            assert self.name == name
        except AssertionError:  # pragma: no cover
            raise Oct2PyError("Thread collision detected")
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
    print(f"Starting {nthreads} threads at {datetime.datetime.now()}")
    threads = []
    for _ in range(nthreads):
        thread = ThreadClass()
        thread.daemon = True
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    print(f"All threads closed at {datetime.datetime.now()}")


if __name__ == "__main__":  # pragma: no cover
    thread_check()

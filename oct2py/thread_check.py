"""oct2py thread check."""
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.


import datetime
import threading

from . import Oct2Py, Oct2PyError, get_log


class ThreadClass(threading.Thread):
    """Octave instance thread"""

    def run(self):
        """
        Create a unique instance of Octave and verify namespace uniqueness.

        Raises
        ======
        Oct2PyError
            If the thread does not successfully demonstrate independence

        """
        octave = Oct2Py()
        # write the same variable name in each thread and read it back
        octave.push("name", self.name)
        name = octave.pull("name")
        now = datetime.datetime.now()  # noqa
        logger = get_log()
        logger.info(f"{self.name} got '{name}' at {now}")
        octave.exit()
        if self.name != name:
            msg = "Thread collision detected"
            raise Oct2PyError(msg)


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
        If the thread does not successfully demonstrate independence.

    """
    logger = get_log()
    logger.info(f"Starting {nthreads} threads at {datetime.datetime.now()}")  # noqa
    threads = []
    for _ in range(nthreads):
        thread = ThreadClass()
        thread.daemon = True
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    logger.info(f"All threads closed at {datetime.datetime.now()}")  # noqa


if __name__ == "__main__":  # pragma: no cover
    thread_check()

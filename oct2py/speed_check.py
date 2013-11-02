"""
.. module:: speed_test
   :synopsis: Checks the speed penalty of the HDF transfers.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>


"""
from __future__ import print_function
import time
import timeit
import numpy as np
from .session import Oct2Py


class SpeedCheck(object):
    """Checks the speed penalty of the Python to Octave bridge.

    Uses timeit to test the raw execution of a Octave command,
    Then tests progressively larger array passing.

    """
    def __init__(self):
        """Create our octave instance and initialize the data array
        """
        self.octave = Oct2Py()
        self.array = []

    def raw_speed(self):
        """Run a fast matlab command and see how long it takes.
        """
        self.octave.run("x = 1")

    def large_array_put(self):
        """Create a large matrix and load it into the octave session.
        """
        self.octave.put('x', self.array)

    def large_array_get(self):
        """Retrieve the large matrix from the octave session
        """
        self.octave.get('x')

    def run(self):
        """Perform the oct2py speed analysis.

        Uses timeit to test the raw execution of an Octave command,
        Then tests progressively larger array passing.

        """
        print('oct2py speed test')
        print('*' * 20)
        time.sleep(1)

        print('Raw speed: ')
        avg = timeit.timeit(self.raw_speed, number=200) / 200
        print('    {0:0.01f} usec per loop'.format(avg * 1e6))
        sides = [1, 10, 100, 1000]
        runs = [200, 200, 100, 10]
        for (side, nruns) in zip(sides, runs):
            self.array = np.reshape(np.arange(side ** 2), (-1))
            print('Put {0}x{1}: '.format(side, side))
            avg = timeit.timeit(self.large_array_put, number=nruns) / nruns
            print('    {0:0.01f} msec'.format(avg * 1e3))

            print('Get {0}x{1}: '.format(side, side))
            avg = timeit.timeit(self.large_array_get, number=nruns) / nruns
            print('    {0:0.01f} msec'.format(avg * 1e3))

        self.octave.close()
        print('*' * 20)
        print('Test complete!')


def speed_test():
    """Checks the speed penalty of the Python to Octave bridge.

    Uses timeit to test the raw execution of a Octave command,
    Then tests progressively larger array passing.

    """
    test = SpeedCheck()
    test.run()


if __name__ == '__main__':
    speed_test()

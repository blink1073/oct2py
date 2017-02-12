# -*- coding: utf-8 -*-
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

from __future__ import print_function, absolute_import
import time
import timeit
import numpy as np
from . import Oct2Py


class SpeedCheck(object):
    """Checks the speed penalty of the Python to Octave bridge.

    Uses timeit to test the raw execution of a Octave command,
    Then tests progressively larger array passing.

    """
    def __init__(self):
        """Create our Octave instance and initialize the data array
        """
        self.octave = Oct2Py()
        self.array = []

    def raw_speed(self):
        """Run a fast Octave command and see how long it takes.
        """
        self.octave.eval("x = 1")

    def large_array_put(self):
        """Create a large matrix and load it into the octave session.
        """
        self.octave.push('x', self.array)

    def large_array_get(self):
        """Retrieve the large matrix from the octave session
        """
        self.octave.pull('x')

    def run(self):
        """Perform the Oct2Py speed analysis.

        Uses timeit to test the raw execution of an Octave command,
        Then tests progressively larger array passing.

        """
        print('Oct2Py speed test')
        print('*' * 20)
        time.sleep(1)

        print('Raw speed: ')
        avg = timeit.timeit(self.raw_speed, number=10) / 10
        print('    {0:0.01f} usec per loop'.format(avg * 1e6))
        sides = [1, 10, 100, 1000]
        runs = [10, 10, 10, 5]
        for (side, nruns) in zip(sides, runs):
            self.array = np.reshape(np.arange(side ** 2), (-1))
            print('Put {0}x{1}: '.format(side, side))
            avg = timeit.timeit(self.large_array_put, number=nruns) / nruns
            print('    {0:0.01f} msec'.format(avg * 1e3))

            print('Get {0}x{1}: '.format(side, side))
            avg = timeit.timeit(self.large_array_get, number=nruns) / nruns
            print('    {0:0.01f} msec'.format(avg * 1e3))

        self.octave.exit()
        print('*' * 20)
        print('Test complete!')


def speed_check():
    """Checks the speed penalty of the Python to Octave bridge.

    Uses timeit to test the raw execution of a Octave command,
    Then tests progressively larger array passing.

    """
    test = SpeedCheck()
    test.run()


if __name__ == '__main__':
    speed_check()

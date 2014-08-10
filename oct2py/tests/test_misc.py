from __future__ import absolute_import, print_function
import logging
import os
import signal
import sys

import numpy as np
import numpy.testing as test
from numpy.testing.decorators import skipif


import oct2py
from oct2py import Oct2Py, Oct2PyError
from oct2py.compat import StringIO


class MiscTests(test.TestCase):

    def setUp(self):
        self.oc = Oct2Py()
        self.oc.addpath(os.path.dirname(__file__))

    def tearDown(self):
        self.oc.close()

    def test_unicode_docstring(self):
        '''Make sure unicode docstrings in Octave functions work'''
        help(self.oc.test_datatypes)

    def test_context_manager(self):
        '''Make sure oct2py works within a context manager'''
        with self.oc as oc1:
            ones = oc1.ones(1)
        assert ones == np.ones(1)
        with self.oc as oc2:
            ones = oc2.ones(1)
        assert ones == np.ones(1)

    def test_singleton_sparses(self):
        '''Make sure a singleton sparse matrix works'''
        import scipy.sparse
        data = scipy.sparse.csc.csc_matrix(1)
        self.oc.put('x', data)
        assert np.allclose(data.toarray(), self.oc.get('x').toarray())
        self.oc.put('y', [data])
        assert np.allclose(data.toarray(), self.oc.get('y').toarray())

    def test_logging(self):
        # create a stringio and a handler to log to it
        def get_handler():
            sobj = StringIO()
            hdlr = logging.StreamHandler(sobj)
            hdlr.setLevel(logging.DEBUG)
            return hdlr
        hdlr = get_handler()
        self.oc.logger.addHandler(hdlr)

        # generate some messages (logged and not logged)
        self.oc.ones(1, verbose=True)

        self.oc.logger.setLevel(logging.DEBUG)
        self.oc.zeros(1)

        # check the output
        lines = hdlr.stream.getvalue().strip().split('\n')
        resp = '\n'.join(lines)
        assert 'zeros(A__)' in resp
        assert 'ans =  1' in resp
        assert lines[0].startswith('load')

        # now make an object with a desired logger
        logger = oct2py.get_log('test')
        hdlr = get_handler()
        logger.addHandler(hdlr)
        logger.setLevel(logging.INFO)
        with Oct2Py(logger=logger) as oc2:
            # generate some messages (logged and not logged)
            oc2.ones(1, verbose=True)
            oc2.logger.setLevel(logging.DEBUG)
            oc2.zeros(1)

        # check the output
        lines = hdlr.stream.getvalue().strip().split('\n')
        resp = '\n'.join(lines)
        assert 'zeros(A__)' in resp
        assert 'ans =  1' in resp
        assert lines[0].startswith('load')

    def test_demo(self):
        from oct2py import demo
        try:
            demo.demo(0.01, interactive=False)
        except AttributeError:
            demo(0.01, interactive=False)

    def test_lookfor(self):
        assert 'cosd' in self.oc.lookfor('cos')

    def test_remove_files(self):
        from oct2py.utils import _remove_temp_files
        _remove_temp_files()

    def test_threads(self):
        from oct2py import thread_test
        thread_test()

    def test_plot(self):
        n = self.oc.figure()
        self.oc.plot([1, 2, 3])
        self.oc.close_(n)

    def test_narg_out(self):
        s = self.oc.svd(np.array([[1, 2], [1, 3]]))
        assert s.shape == (2, 1)
        U, S, V = self.oc.svd([[1, 2], [1, 3]])
        assert U.shape == S.shape == V.shape == (2, 2)

    def test_help(self):
        help(self.oc)

    def test_trailing_underscore(self):
        x = self.oc.ones_()
        assert np.allclose(x, np.ones(1))

    def test_using_closed_session(self):
        with Oct2Py() as oc:
            oc.close()
            test.assert_raises(Oct2PyError, oc.call, 'ones')

    def test_keyboard(self):
        self.oc._eval('a=1')

        stdin = sys.stdin
        stdout = sys.stdout
        output = StringIO()
        sys.stdin = StringIO('a\nexit')
        self.oc._session.stdout = output
        try:
            self.oc.keyboard(timeout=3)
        except Oct2PyError as e:  # pragma: no cover
            if 'session timed out' in str(e).lower():
                # the keyboard command is not supported
                # (likely using Octave 3.2)
                return
            else:
                raise(e)
        sys.stdin.flush()
        sys.stdin = stdin
        self.oc._session.stdout = stdout

        out = output.getvalue()
        assert 'Entering Octave Debug Prompt...' in out
        assert 'a =  1' in out

    def test_func_without_docstring(self):
        out = self.oc.test_nodocstring(5)
        assert out == 5
        assert 'user-defined function' in self.oc.test_nodocstring.__doc__
        assert os.path.dirname(__file__) in self.oc.test_nodocstring.__doc__

    def test_func_noexist(self):
        test.assert_raises(Oct2PyError, self.oc.call, 'oct2py_dummy')

    def test_timeout(self):
        with Oct2Py(timeout=2) as oc:
            oc.sleep(2.1, timeout=5)
            test.assert_raises(Oct2PyError, oc.sleep, 3)

    def test_call_path(self):
        with Oct2Py() as oc:
            oc.addpath(os.path.dirname(__file__))
            DATA = oc.call('test_datatypes.m')
        assert DATA.string.basic == 'spam'

        with Oct2Py() as oc:
            path = os.path.join(os.path.dirname(__file__), 'test_datatypes.m')
            DATA = oc.call(path)
        assert DATA.string.basic == 'spam'

    def test_long_variable_name(self):
        name = 'this_variable_name_is_over_32_char'
        self.oc.put(name, 1)
        x = self.oc.get(name)
        assert x == 1

    def test_syntax_error_embedded(self):
        test.assert_raises(Oct2PyError, self.oc.run, """eval("a='1")""")
        self.oc.put('b', 1)
        x = self.oc.get('b')
        assert x == 1

    def test_oned_as(self):
        x = np.ones(10)
        self.oc.put('x', x)
        assert self.oc.get('x').shape == x[:, np.newaxis].T.shape
        oc = Oct2Py(oned_as='column')
        oc.put('x', x)
        assert oc.get('x').shape == x[:, np.newaxis].shape

    def test_temp_dir(self):
        oc = Oct2Py(temp_dir='.')
        thisdir = os.path.dirname(os.path.abspath('.'))
        assert oc._reader.out_file.startswith(thisdir)
        assert oc._writer.in_file.startswith(thisdir)

    @skipif(not hasattr(signal, 'alarm'))
    def test_interrupt(self):

        def receive_signal(signum, stack):
            raise KeyboardInterrupt

        signal.signal(signal.SIGALRM, receive_signal)

        signal.alarm(5)
        self.oc.run("sleep(10);kladjflsd")

        self.oc.put('c', 10)
        x = self.oc.get('c')
        assert x == 10

    def test_clear(self):
        """Make sure clearing variables does not mess anything up."""
        self.oc.clear()

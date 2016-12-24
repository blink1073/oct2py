from __future__ import absolute_import, print_function
import glob
import logging
import os
import shutil
import sys
import tempfile
import threading
import time

try:
    import thread
except ImportError:
    import _thread as thread

import numpy as np
import numpy.testing as test

import oct2py
from oct2py import Oct2Py, Oct2PyError
from oct2py.compat import StringIO


class MiscTests(test.TestCase):

    def setUp(self):
        self.oc = Oct2Py()
        self.oc.addpath(os.path.dirname(__file__))

    def tearDown(self):
        self.oc.exit()

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
        self.oc.push('x', data)
        assert np.allclose(data.toarray(), self.oc.pull('x').toarray())
        self.oc.push('y', [data])
        assert np.allclose(data.toarray(), self.oc.pull('y').toarray())

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
        print(resp)
        assert 'load ' in resp

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
        assert 'load ' in resp

    def test_demo(self):
        from oct2py import demo
        try:
            demo.demo(0.01, interactive=False)
        except AttributeError:
            demo(0.01, interactive=False)

    def test_threads(self):
        from oct2py import thread_check
        try:
            thread_check()
        except TypeError:
            thread_check.thread_check()

    def test_speed_check(self):
        from oct2py import speed_check
        try:
            speed_check()
        except TypeError:
            speed_check.speed_check()

    def test_plot(self):
        plot_dir = tempfile.mkdtemp().replace('\\', '/')
        self.oc.plot([1, 2, 3], plot_dir=plot_dir)
        assert glob.glob("%s/*" % plot_dir)
        assert self.oc.extract_figures(plot_dir)

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

    def test_using_exited_session(self):
        with Oct2Py() as oc:
            oc.exit()
            test.assert_raises(Oct2PyError, oc.eval, 'ones')

    def test_keyboard(self):
        self.oc.eval('a=1')

        stdin = sys.stdin
        sys.stdin = StringIO('a\ndbquit\n')

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

        self.oc.pull('a') == 1

    def test_func_without_docstring(self):
        out = self.oc.test_nodocstring(5)
        assert out == 5
        assert 'user-defined function' in self.oc.test_nodocstring.__doc__
        assert os.path.dirname(__file__) in self.oc.test_nodocstring.__doc__

    def test_func_noexist(self):
        test.assert_raises(Oct2PyError, self.oc.eval, 'oct2py_dummy')

    def test_timeout(self):
        with Oct2Py(timeout=2) as oc:
            oc.sleep(2.1, timeout=5)
            test.assert_raises(Oct2PyError, oc.sleep, 3)

    def test_call_path(self):
        with Oct2Py() as oc:
            oc.addpath(os.path.dirname(__file__))
            DATA = oc.test_datatypes()
        assert DATA.string.basic == 'spam'

    def test_long_variable_name(self):
        name = 'this_variable_name_is_over_32_char'
        self.oc.push(name, 1)
        x = self.oc.pull(name)
        assert x == 1

    def test_syntax_error_embedded(self):
        test.assert_raises(Oct2PyError, self.oc.eval, """eval("a='1")""")
        self.oc.push('b', 1)
        x = self.oc.pull('b')
        assert x == 1

    def test_oned_as(self):
        x = np.ones(10)
        self.oc.push('x', x)
        assert self.oc.pull('x').shape == x[:, np.newaxis].T.shape
        oc = Oct2Py(oned_as='column')
        oc.push('x', x)
        assert oc.pull('x').shape == x[:, np.newaxis].shape
        oc.exit()

    def test_temp_dir(self):
        temp_dir = tempfile.mkdtemp()
        oc = Oct2Py(temp_dir=temp_dir)
        oc._reader.create_file(oc.temp_dir)
        oc._writer.create_file(oc.temp_dir, [])
        assert oc._reader.out_file.startswith(temp_dir)
        assert oc._writer.in_file.startswith(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)
        oc.exit()

    def test_clear(self):
        """Make sure clearing variables does not mess anything up."""
        self.oc.clear()

    def test_multiline_statement(self):
        sobj = StringIO()
        hdlr = logging.StreamHandler(sobj)
        hdlr.setLevel(logging.DEBUG)
        self.oc.logger.addHandler(hdlr)

        self.oc.logger.setLevel(logging.DEBUG)

        ans = self.oc.eval("""
    a =1
    a + 1;
    b = 3
    b + 1""")
        text = hdlr.stream.getvalue().strip()
        assert ans == 4
        lines = text.splitlines()
        assert lines[-1] == 'ans =  4'
        assert lines[-2] == 'b =  3'
        assert lines[-3] == 'a =  1'

    def test_empty_values(self):
        self.oc.push('a', '')
        assert self.oc.pull('a') == ''

        self.oc.push('a', [])
        assert self.oc.pull('a') == []

        self.oc.push('a', None)
        assert np.isnan(self.oc.pull('a'))

        assert self.oc.struct() == [None]

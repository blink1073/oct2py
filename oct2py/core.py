# -*- coding: utf-8 -*-
# Copyright (c) oct2py developers.
# Distributed under the terms of the MIT License.

from __future__ import print_function, absolute_import, division

import logging
import os
import os.path as osp
import tempfile
import warnings

import numpy as np
from metakernel.pexpect import EOF, TIMEOUT
from octave_kernel.kernel import OctaveEngine, STDIN_PROMPT

from .io import read_file, write_file, Cell, StructArray
from .utils import Oct2PyError, get_log
from .compat import unicode, input, string_types
from .dynamic import (
    _make_function_ptr_instance, _make_variable_ptr_instance,
    _make_user_class, OctavePtr)


HERE = osp.realpath(osp.dirname(__file__))


class Oct2Py(object):

    """Manages an Octave session.

    Uses MAT files to pass data between Octave and Numpy.
    The function must either exist as an m-file in this directory or
    on Octave's path.
    The first command will take about 0.5s for Octave to load up.
    The subsequent commands will be much faster.

    You may provide a logger object for logging events, or the oct2py.get_log()
    default will be used.  When calling commands, logger.info() will be used
    to stream output, unless a `stream_handler` is provided.

    Parameters
    ----------
    logger : logging object, optional
        Optional logger to use for Oct2Py session
    timeout : float, optional
        Timeout in seconds for commands
    oned_as : {'row', 'column'}, optional
        If 'column', write 1-D numpy arrays as column vectors.
        If 'row', write 1-D numpy arrays as row vectors.}
    temp_dir : str, optional
        If specified, the session's MAT files will be created in the
        directory, otherwise a default directory is used.  This can be
        a shared memory (tmpfs) path.
    convert_to_float : bool, optional
        If true, convert integer types to float when passing to Octave.
    backend: string, optional
        The graphics_toolkit to use for plotting.
    """

    def __init__(self, logger=None, timeout=None,
                 oned_as='row', temp_dir=None, convert_to_float=True,
                 backend=None):
        """Start Octave and set up the session.
        """
        self._oned_as = oned_as
        self._engine = None
        self._logger = None
        self.logger = logger
        self.timeout = timeout
        self.backend = backend or 'default'
        self.temp_dir = temp_dir or tempfile.mkdtemp()
        self.convert_to_float = convert_to_float
        self._user_classes = dict()
        self._function_ptrs = dict()
        self.restart()

    @property
    def logger(self):
        """The logging instance used by the session."""
        return self._logger

    @logger.setter
    def logger(self, value):
        self._logger = value or get_log()
        if self._engine:
            self._engine.logger = self._logger

    def __enter__(self):
        """Return octave object, restart session if necessary"""
        if not self._engine:
            self.restart()
        return self

    def __exit__(self, type, value, traceback):
        """Close session"""
        self.exit()

    def exit(self):
        """Quits this octave session and cleans up.
        """
        if self._engine:
            self._engine.repl.terminate()
        self._engine = None

    def push(self, name, var, timeout=None, verbose=True):
        """
        Put a variable or variables into the Octave session.

        Parameters
        ----------
        name : str or list
            Name of the variable(s).
        var : object or list
            The value(s) to pass.
        timeout : float
            Time to wait for response from Octave (per line).
        **kwargs: Deprecated kwargs, ignored.

        Examples
        --------
        >>> from oct2py import octave
        >>> y = [1, 2]
        >>> octave.push('y', y)
        >>> octave.pull('y')
        array([[1., 2.]])
        >>> octave.push(['x', 'y'], ['spam', [1, 2, 3, 4]])
        >>> octave.pull(['x', 'y'])  # doctest: +SKIP
        [u'spam', array([[1, 2, 3, 4]])]

        Notes
        -----
        Integer type arguments will be converted to floating point
        unless `convert_to_float=False`.

        """
        if isinstance(name, (str, unicode)):
            name = [name]
            var = [var]

        for (n, v) in zip(name, var):
            self.feval('assignin', 'base', n, v, nout=0, timeout=timeout,
                       verbose=verbose)

    def pull(self, var, timeout=None, verbose=True):
        """
        Retrieve a value or values from the Octave session.

        Parameters
        ----------
        var : str or list
            Name of the variable(s) to retrieve.
        timeout : float, optional.
            Time to wait for response from Octave (per line).
        **kwargs: Deprecated kwargs, ignored.

        Returns
        -------
        out : object
            Object returned by Octave.

        Raises
        ------
        Oct2PyError
            If the variable does not exist in the Octave session.

        Examples
        --------
          >>> from oct2py import octave
          >>> y = [1, 2]
          >>> octave.push('y', y)
          >>> octave.pull('y')
          array([[1., 2.]])
          >>> octave.push(['x', 'y'], ['spam', [1, 2, 3, 4]])
          >>> octave.pull(['x', 'y'])  # doctest: +SKIP
          [u'spam', array([[1, 2, 3, 4]])]

        """
        if isinstance(var, (str, unicode)):
            var = [var]
        outputs = []
        for name in var:
            exist = self._exist(name)
            if exist == 1:
                outputs.append(self.feval('evalin', 'base', name,
                                          timeout=timeout, verbose=verbose))
            else:
                outputs.append(self.get_pointer(name, timeout=timeout))

        if len(outputs) == 1:
            return outputs[0]
        return outputs

    def get_pointer(self, name, timeout=None):
        """Get a pointer to a named object in the Octave workspace.

        Parameters
        ----------
        name: str
            The name of the object in the Octave workspace.
        timemout: float, optional.
            Time to wait for response from Octave (per line).

        Examples
        --------
        >>> from oct2py import octave
        >>> octave.eval('foo = [1, 2];')
        >>> ptr = octave.get_pointer('foo')
        >>> ptr.value
        array([[1., 2.]])
        >>> ptr.address
        'foo'
        >>> # Can be passed as an argument
        >>> octave.disp(ptr)  # doctest: +SKIP
        1  2

        >>> from oct2py import octave
        >>> sin = octave.get_pointer('sin')  # equivalent to `octave.sin`
        >>> sin.address
        '@sin'
        >>> x = octave.quad(sin, 0, octave.pi())
        >>> x
        2.0

        Notes
        -----
        Pointers can be passed to `feval` or dynamic functions as function arguments.  A pointer passed as a nested value will be passed by value instead.

        Raises
        ------
        Oct2PyError
            If the variable does not exist in the Octave session or is of
            unknown type.

        Returns
        -------
        A variable, object, user class, or function pointer as appropriate.
        """
        exist = self._exist(name)
        isobject = self._isobject(name, exist)

        if exist == 0:
            raise Oct2PyError('"%s" is undefined' % name)

        elif exist == 1:
            return _make_variable_ptr_instance(self, name)

        elif isobject:
            return self._get_user_class(name)

        elif exist in [2, 3, 5]:
            return self._get_function_ptr(name)

        raise Oct2PyError('Unknown type for object "%s"' % name)

    def extract_figures(self, plot_dir, remove=False):
        """Extract the figures in the directory to IPython display objects.

        Parameters
        ----------
        plot_dir: str
            The plot dir where the figures were created.
        remove: bool, optional.
            Whether to remove the plot directory after saving.
        """
        figures = self._engine.extract_figures(plot_dir, remove)
        return figures

    def feval(self, func_path, *func_args, **kwargs):
        """Run a function in Octave and return the result.

        Parameters
        ----------
        func_path: str
            Name of function to run or a path to an m-file.
        func_args: object, optional
            Args to send to the function.
        nout: int or str, optional. 
            Desired number of return arguments, defaults to 1. If nout 
            value is 'max_nout', get_max_nout() will be used.
        store_as: str, optional
            If given, saves the result to the given Octave variable name
            instead of returning it.
        verbose : bool, optional
            Log Octave output at INFO level.  If False, log at DEBUG level.
        stream_handler: callable, optional
            A function that is called for each line of output from the
            evaluation.
        timeout: float, optional
            The timeout in seconds for the call.
        plot_dir: str, optional
            If specificed, save the session's plot figures to the plot
            directory instead of displaying the plot window.
        plot_backend: str, optional
            The plotting back end to use.
        plot_name : str, optional
            Saved plots will start with `plot_name` and
            end with "_%%.xxx' where %% is the plot number and
            xxx is the `plot_format`.
        plot_format: str, optional
            The format in which to save the plot.
        plot_width: int, optional
            The plot with in pixels.
        plot_height: int, optional
            The plot height in pixels.

        Notes
        -----
        The function arguments passed follow Octave calling convention, not
        Python. That is, all values must be passed as a comma separated list,
        not using `x=foo` assignment.

        Examples
        --------
        >>> from oct2py import octave
        >>> cell = octave.feval('cell', 10, 10, 10)
        >>> cell.shape
        (10, 10, 10)

        >>> from oct2py import octave
        >>> x = octave.feval('linspace', 0, octave.pi() / 2)
        >>> x.shape
        (1, 100)

        >>> from oct2py import octave
        >>> x = octave.feval('svd', octave.hilb(3))
        >>> x
        array([[1.40831893],
               [0.12232707],
               [0.00268734]])
        >>> # specify three return values
        >>> (u, v, d) = octave.feval('svd', octave.hilb(3), nout=3)
        >>> u.shape
        (3, 3)

        Returns
        -------
        The Python value(s) returned by the Octave function call.
        """
        if not self._engine:
            raise Oct2PyError('Session is not open')

        nout = kwargs.get('nout', None)
        if nout is None:
            nout = 1
        elif nout == 'max_nout':
            nout = self._get_max_nout(func_path)

        plot_dir = kwargs.get('plot_dir')

        # Choose appropriate plot backend.
        default_backend = 'inline' if plot_dir else self.backend
        backend = kwargs.get('plot_backend', default_backend)

        settings = dict(backend=backend,
                        format=kwargs.get('plot_format'),
                        name=kwargs.get('plot_name'),
                        width=kwargs.get('plot_width'),
                        height=kwargs.get('plot_height'),
                        resolution=kwargs.get('plot_res'))
        self._engine.plot_settings = settings

        dname = osp.dirname(func_path)
        fname = osp.basename(func_path)
        func_name, ext = osp.splitext(fname)
        if ext and not ext == '.m':
            raise TypeError('Need to give path to .m file')

        if func_name == 'clear':
            raise Oct2PyError('Cannot use `clear` command directly, use' +
                              ' eval("clear(var1, var2)")')

        stream_handler = kwargs.get('stream_handler')
        verbose = kwargs.get('verbose', True)
        store_as = kwargs.get('store_as', '')
        timeout = kwargs.get('timeout', self.timeout)
        if not stream_handler:
            stream_handler = self.logger.info if verbose else self.logger.debug

        return self._feval(func_name, func_args, dname=dname, nout=nout,
                          timeout=timeout, stream_handler=stream_handler,
                          store_as=store_as, plot_dir=plot_dir)

    def eval(self, cmds, verbose=True, timeout=None, stream_handler=None,
             temp_dir=None, plot_dir=None, plot_name='plot', plot_format='svg', plot_backend=None,
             plot_width=None, plot_height=None, plot_res=None,
             nout=0, **kwargs):
        """
        Evaluate an Octave command or commands.

        Parameters
        ----------
        cmds : str or list
            Commands(s) to pass to Octave.
        verbose : bool, optional
             Log Octave output at INFO level.  If False, log at DEBUG level.
        stream_handler: callable, optional
            A function that is called for each line of output from the
            evaluation.
        timeout : float, optional
            Time to wait for response from Octave (per line).  If not given,
            the instance `timeout` is used.
        nout : int, optional.
            The desired number of returned values, defaults to 0.  If nout
            is 0, the `ans` will be returned as the return value.
        temp_dir: str, optional
            If specified, the session's MAT files will be created in the
            directory, otherwise a the instance `temp_dir` is used.
            a shared memory (tmpfs) path.
        plot_dir: str, optional
            If specificed, save the session's plot figures to the plot
            directory instead of displaying the plot window.
        plot_name : str, optional
            Saved plots will start with `plot_name` and
            end with "_%%.xxx' where %% is the plot number and
            xxx is the `plot_format`.
        plot_format: str, optional
            The format in which to save the plot (PNG by default).
        plot_width: int, optional
            The plot with in pixels.
        plot_height: int, optional
            The plot height in pixels.
        plot_backend: str, optional
            The plot backend to use.
        plot_res: int, optional
            The plot resolution in pixels per inch.
        **kwargs Deprectated kwargs.

        Examples
        --------
        >>> from oct2py import octave
        >>> octave.eval('disp("hello")') # doctest: +SKIP
        hello
        >>> x = octave.eval('round(quad(@sin, 0, pi/2));')
        >>> x
        1.0

        >>> a = octave.eval('disp("hello");1;')  # doctest: +SKIP
        hello
        >>> a = octave.eval('disp("hello");1;', verbose=False)
        >>> a
        1.0

        >>> from oct2py import octave
        >>> lines = []
        >>> octave.eval('for i = 1:3; disp(i);end', \
                        stream_handler=lines.append)
        >>> lines  # doctest: +SKIP
        [' 1', ' 2', ' 3']

        Returns
        -------
        out : object
            Octave "ans" variable, or None.

        Notes
        -----
        The deprecated `log` kwarg will temporarily set the `logger` level to
        `WARN`.  Using the `logger` settings directly is preferred.
        The deprecated `return_both` kwarg will still work, but the preferred
        method is to use the `stream_handler`.  If `stream_handler` is given,
        the `return_both` kwarg will be honored but will give an empty string
        as the reponse.

        Raises
        ------
        Oct2PyError
            If the command(s) fail.
        """
        if isinstance(cmds, (str, unicode)):
            cmds = [cmds]

        prev_temp_dir = self.temp_dir
        self.temp_dir = temp_dir or self.temp_dir
        prev_log_level = self.logger.level

        if kwargs.get('log') is False:
            self.logger.setLevel(logging.WARN)

        for name in ['log', 'return_both']:
            if name not in kwargs:
                continue
            msg = 'Using deprecated `%s` kwarg, see docs on `Oct2Py.eval()`'
            warnings.warn(msg % name, stacklevel=2)

        return_both = kwargs.pop('return_both', False)
        lines = []
        if return_both and not stream_handler:
            stream_handler = lines.append

        ans = None
        for cmd in cmds:
            resp = self.feval('evalin', 'base', cmd,
                              nout=nout, timeout=timeout,
                              stream_handler=stream_handler,
                              verbose=verbose, plot_dir=plot_dir,
                              plot_name=plot_name, plot_format=plot_format,
                              plot_backend=plot_backend,
                              plot_width=plot_width, plot_height=plot_height,
                              plot_res=plot_res)
            if resp is not None:
                ans = resp

        self.temp_dir = prev_temp_dir
        self.logger.setLevel(prev_log_level)

        if return_both:
            return '\n'.join(lines), ans
        return ans

    def restart(self):
        """Restart an Octave session in a clean state
        """
        if self._engine:
            self._engine.repl.terminate()

        if 'OCTAVE_EXECUTABLE' not in os.environ and 'OCTAVE' in os.environ:
            os.environ['OCTAVE_EXECUTABLE'] = os.environ['OCTAVE']

        self._engine = OctaveEngine(stdin_handler=self._handle_stdin,
                                    logger=self.logger)

        # Add local Octave scripts.
        self._engine.eval('addpath("%s");' % HERE.replace(osp.sep, '/'))

    def _feval(self, func_name, func_args=(), dname='', nout=0,
              timeout=None, stream_handler=None, store_as='', plot_dir=None):
        """Run the given function with the given args.
        """
        engine = self._engine
        if engine is None:
            raise Oct2PyError('Session is closed')

        # Set up our mat file paths.
        out_file = osp.join(self.temp_dir, 'writer.mat')
        out_file = out_file.replace(osp.sep, '/')
        in_file = osp.join(self.temp_dir, 'reader.mat')
        in_file = in_file.replace(osp.sep, '/')

        func_args = list(func_args)
        ref_indices = []
        for (i, value) in enumerate(func_args):
            if isinstance(value, OctavePtr):
                ref_indices.append(i + 1)
                func_args[i] = value.address
        ref_indices = np.array(ref_indices)

        # Save the request data to the output file.
        req = dict(func_name=func_name, func_args=tuple(func_args),
                   dname=dname or '', nout=nout,
                   store_as=store_as or '',
                   ref_indices=ref_indices)

        write_file(req, out_file, oned_as=self._oned_as,
                   convert_to_float=self.convert_to_float)

        # Set up the engine and evaluate the `_pyeval()` function.
        engine.line_handler = stream_handler or self.logger.info
        if timeout is None:
            timeout = self.timeout

        try:
            engine.eval('_pyeval("%s", "%s");' % (out_file, in_file),
                        timeout=timeout)
        except KeyboardInterrupt as e:
            stream_handler(engine.repl.interrupt())
            raise
        except TIMEOUT:
            stream_handler(engine.repl.interrupt())
            raise Oct2PyError('Timed out, interrupting')
        except EOF:
            if not self._engine:
                return
            stream_handler(engine.repl.child.before)
            self.restart()
            raise Oct2PyError('Session died, restarting')

        # Read in the output.
        resp = read_file(in_file, self)
        if resp['err']:
            msg = self._parse_error(resp['err'])
            raise Oct2PyError(msg)

        result = resp['result'].ravel().tolist()
        if isinstance(result, list) and len(result) == 1:
            result = result[0]

        # Check for sentinel value.
        if (isinstance(result, Cell) and
                result.size == 1 and
                isinstance(result[0], string_types) and
                result[0] == '__no_value__'):
            result = None

        if plot_dir:
            self._engine.make_figures(plot_dir)

        return result

    def _parse_error(self, err):
        """Create a traceback for an Octave evaluation error.
        """
        self.logger.debug(err)
        stack = err.get('stack', [])
        if not err['message'].startswith('parse error:'):
            err['message'] = 'error: ' + err['message']
        errmsg = 'Octave evaluation error:\n%s' % err['message']

        if not isinstance(stack, StructArray):
            return errmsg

        errmsg += '\nerror: called from:'
        for item in stack[:-1]:
            errmsg += '\n    %(name)s at line %(line)d' % item
            try:
                errmsg += ', column %(column)d' % item
            except Exception:
                pass
        return errmsg

    def _handle_stdin(self, line):
        """Handle a stdin request from the session."""
        return input(line.replace(STDIN_PROMPT, ''))

    def _get_doc(self, name):
        """
        Get the documentation of an Octave procedure or object.

        Parameters
        ----------
        name : str
            Function name to search for.

        Returns
        -------
        out : str
          Documentation string.

        Raises
        ------
        Oct2PyError
           If the procedure or object function has a syntax error.

        """
        doc = 'No documentation for %s' % name

        engine = self._engine

        doc = engine.eval('help("%s")' % name, silent=True)

        if 'syntax error:' in doc.lower():
            raise Oct2PyError(doc)

        if 'error:' in doc.lower():
            doc = engine.eval('type("%s")' % name, silent=True)
            doc = '\n'.join(doc.splitlines()[:3])

        default = self.feval.__doc__
        default = '        ' + default[default.find('func_args:'):]
        default = '\n'.join([line[8:] for line in default.splitlines()])

        doc = '\n'.join(doc.splitlines())
        doc = '\n' + doc + '\n\nParameters\n----------\n' + default
        doc += '\n**kwargs - Deprecated keyword arguments\n\n'
        doc += 'Notes\n-----\n'
        doc += 'Keyword arguments to dynamic functions are deprecated.\n'
        doc += 'The `plot_*` kwargs will be ignored, but the rest will\n'
        doc += 'used as key - value pairs as in version 3.x.\n'
        doc += 'Use `set_plot_settings()` for plot settings, and use\n'
        doc += '`func_args` directly for key - value pairs.'
        return doc

    def _exist(self, name):
        """Test whether a name exists and return the name code.

        Raises an error when the name does not exist.
        """
        cmd = 'exist("%s")' % name
        resp = self._engine.eval(cmd, silent=True).strip()
        exist = int(resp.split()[-1])
        if exist == 0:
            cmd = 'class(%s)' % name
            resp = self._engine.eval(cmd, silent=True).strip()
            if 'error:' in resp:
                msg = 'Value "%s" does not exist in Octave workspace'
                raise Oct2PyError(msg % name)
            else:
                exist = 2
        return exist

    def _isobject(self, name, exist):
        """Test whether the name is an object."""
        if exist in [2, 5]:
            return False
        cmd = 'isobject(%s)' % name
        resp = self._engine.eval(cmd, silent=True).strip()
        return resp == 'ans =  1'

    def _get_function_ptr(self, name):
        """Get or create a function pointer of the given name."""
        func = _make_function_ptr_instance
        self._function_ptrs.setdefault(name, func(self, name))
        return self._function_ptrs[name]

    def _get_user_class(self, name):
        """Get or create a user class of the given type."""
        self._user_classes.setdefault(name, _make_user_class(self, name))
        return self._user_classes[name]

    def __getattr__(self, attr):
        """Automatically creates a wapper to an Octave function or object.

        Adapted from the mlabwrap project.
        """
        # needed for help(Oct2Py())
        if attr.startswith('__'):
            return super(Oct2Py, self).__getattr__(attr)

        # close_ -> close
        if attr[-1] == "_":
            name = attr[:-1]
        else:
            name = attr

        if self._engine is None:
            raise Oct2PyError('Session is closed')

        # Make sure the name exists.
        exist = self._exist(name)

        if exist not in [2, 3, 5, 103]:
            msg = 'Name "%s" is not a valid callable, use `pull` for variables'
            raise Oct2PyError(msg % name)

        if name == 'clear':
            raise Oct2PyError('Cannot use `clear` command directly, use' +
                              ' `eval("clear(var1, var2)")`')

        # Check for user defined class.
        if self._isobject(name, exist):
            obj = self._get_user_class(name)
        else:
            obj = self._get_function_ptr(name)

        # !!! attr, *not* name, because we might have python keyword name!
        setattr(self, attr, obj)

        return obj

    def _get_max_nout(self, func_path):
        """Get or count maximum nout of .m function."""
        
        if not osp.isabs(func_path):
            func_path = self.which(func_path)

        nout = 0
        status = 'NOT FUNCTION'
        with open(func_path, encoding='utf8') as f:
            for l in f: 
                if l[0] != 'f': #not function
                    if status == 'NOT FUNCTION':
                        continue
                l = l.translate(str.maketrans('', '', '[]()')).split()
                try:
                    l.remove('function')
                except:
                    pass
                for s in l:
                    if s == '...':
                        status = 'FUNCTION'
                        continue
                    if s != '=':
                        nout += 1
                    else:
                        return nout
        return nout
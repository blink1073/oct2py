"""
.. module:: core
   :synopsis: Main module for oct2py package.
              Contains the core session object Oct2Py

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import print_function, absolute_import, division

import os
import tempfile
import warnings

import numpy as np
from metakernel.pexpect import EOF, TIMEOUT
from octave_kernel.kernel import OctaveEngine, STDIN_PROMPT

from .matwrite import Writer
from .matread import Reader
from .utils import get_nout, Oct2PyError, get_log
from .compat import unicode, input
from .dynamic import (
    _make_function_ptr_instance, _make_variable_ptr_instance,
    _make_user_class, OctavePtr)


# TODO:
#       revert to the original test suite and get those tests to pass.
#       add tests for:
#            get_pointer - variable, function, class, object instance
#            set_plot_settings
#            pull - object
#            feval - store_as, variable ptr, function ptr, class ptr,
#                    object instance ptr


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
    executable : str, optional
        Name of the Octave executable, can be a system path.  If this is not
        given, we look for an OCTAVE_EXECUTABLE environmental variable.
        The fallback is to call "octave-cli" or "octave".
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
    """

    def __init__(self, executable=None, logger=None, timeout=None,
                 oned_as='row', temp_dir=None, convert_to_float=True):
        """Start Octave and set up the session.
        """
        self._oned_as = oned_as
        self._executable = executable

        self.timeout = timeout
        if logger is not None:
            self.logger = logger
        else:
            self.logger = get_log()
        self._engine = None
        self.temp_dir = temp_dir or tempfile.mkdtemp()
        self.convert_to_float = convert_to_float
        self._user_classes = dict()
        self._function_ptrs = dict()
        self._writer = Writer()
        self._reader = Reader(self)
        self.restart()

    def __enter__(self):
        """Return octave object, restart session if necessary"""
        if not self._engine:
            self.restart()
        return self

    def __exit__(self, type, value, traceback):
        """Close session"""
        self.exit()

    def exit(self):
        """Quits this octave session and removes temp files
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
        array([[ 1.,  2.]])
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
          array([[ 1.,  2.]])
          >>> octave.push(['x', 'y'], ['spam', [1, 2, 3, 4]])
          >>> octave.pull(['x', 'y'])  # doctest: +SKIP
          [u'spam', array([[1, 2, 3, 4]])]

        """
        if isinstance(var, (str, unicode)):
            var = [var]
        outputs = []
        for name in var:
            exist = self._exist(name)
            isobject = self._isobject(name, exist)
            if exist == 1 and not isobject:
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

        if exist == 1 and isobject:
            class_name = self.eval('class(%s);' % name)
            cls = self._get_user_class(class_name)
            return cls.from_name(name)

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

    def feval(self, func_path, *func_args, nout=None, verbose=True,
              store_as=None, timeout=None, stream_handler=None,
              plot_dir=None, plot_name='plot', plot_format='svg',
              plot_width=None, plot_height=None,
              plot_res=None):
        """Run a function in Octave and return the result.

        Parameters
        ----------
        func_path: str
            Name of function to run or a path to an m-file.
        func_args: object, optional
            Args to send to the function.
        nout: int, optional
            Desired number of return arguments.  If not given, the number
            of arguments will be inferred from the return value(s).
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

        Returns
        -------
        The Python value(s) returned by the Octave function call.
        """
        if nout is None:
            nout = get_nout() or 1

        settings = dict(backend='inline' if plot_dir else 'gnuplot',
                        format=plot_format,
                        name=plot_name,
                        width=plot_width,
                        height=plot_height,
                        resolution=plot_res)
        self._engine.plot_settings = settings

        dname = os.path.dirname(func_path)
        fname = os.path.basename(func_path)
        func_name, ext = os.path.splitext(fname)
        if ext and not ext == '.m':
            raise TypeError('Need to give path to .m file')

        if func_name == 'clear':
            raise Oct2PyError('Cannot use `clear` command directly, use' +
                              ' eval("clear(var1, var2)")')

        if not stream_handler:
            stream_handler = self.logger.info if verbose else self.logger.debug

        return self._feval(func_name, *func_args, dname=dname, nout=nout,
                          timeout=timeout, stream_handler=stream_handler,
                          store_as=store_as, plot_dir=plot_dir)

    def eval(self, cmds, verbose=True, timeout=None, stream_handler=None,
             plot_dir=None, plot_name='plot', plot_format='svg',
             plot_width=None, plot_height=None, plot_res=None, **kwargs):
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
            Time to wait for response from Octave (per line).
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
        plot_res: int, optional
            The plot resolution in pixels per inch.
        **kwargs Deprectated kwargs.

        Returns
        -------
        out : object
            Octave "ans" variable, or None.

        Notes
        -----
        The deprecated `temp_dir` kwarg will be ignored in favor of the
        instance-level `temp_dir`.
        The deprecated `log` kwarg will be ignored.
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

        for name in ['log', 'return_both', 'temp_dir']:
            if name not in kwargs:
                continue
            msg = 'Using deprecated `%s` kwarg, see docs on `eval()`' % name
            warnings.warn(msg)

        return_both = kwargs.pop('return_both', False)
        lines = []
        if return_both and not stream_handler:
            stream_handler = lines.append

        ans = None
        for cmd in cmds:
            resp = self.feval('evalin', 'base', cmd,
                              nout=0, timeout=timeout,
                              stream_handler=stream_handler,
                              verbose=verbose, plot_dir=plot_dir,
                              plot_name=plot_name, plot_format=plot_format,
                              plot_width=plot_width, plot_height=plot_height,
                              plot_res=plot_res)
            if resp is not None:
                ans = resp

        if return_both:
            return '\n'.join(lines), ans
        return ans

    def restart(self):
        """Restart an Octave session in a clean state
        """
        if self._engine:
            self._engine.repl.terminate()

        executable = self._executable
        if executable:
            os.environ['OCTAVE_EXECUTABLE'] = executable
        if 'OCTAVE_EXECUTABLE' not in os.environ and 'OCTAVE' in os.environ:
            os.environ['OCTAVE_EXECUTABLE'] = os.environ['OCTAVE']

        self._engine = OctaveEngine(stdin_handler=self._handle_stdin)

        # Add local Octave scripts.
        here = os.path.realpath(os.path.dirname(__file__))
        self._engine.eval('addpath("%s");' % here.replace(os.path.sep, '/'))

    def _feval(self, func_name, *func_args, dname='', nout=0,
              timeout=None, stream_handler=None, store_as='', plot_dir=None):
        """Run the given function with the given args.
        """
        engine = self._engine
        if engine is None:
            raise Oct2PyError('Session is closed')

        # Set up our mat file paths.
        out_file = os.path.join(self.temp_dir, 'writer.mat')
        out_file = out_file.replace(os.path.sep, '/')
        in_file = os.path.join(self.temp_dir, 'reader.mat')
        in_file = in_file.replace(os.path.sep, '/')

        func_args = list(func_args)
        ref_indices = []
        for (i, value) in enumerate(func_args):
            if isinstance(value, OctavePtr):
                ref_indices.append(i + 1)
                func_args[i] = value._address
        ref_indices = np.array(ref_indices)

        # Save the request data to the output file.
        req = dict(func_name=func_name, func_args=tuple(func_args),
                   dname=dname or '', nout=nout or 0,
                   store_as=store_as or '',
                   ref_indices=ref_indices)

        self._writer.write_file(req, out_file, oned_as=self._oned_as,
                                convert_to_float=self.convert_to_float)

        # Set up the engine and evaluate the `_pyeval()` function.

        engine.stream_handler = stream_handler or self.logger.info

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
            stream_handler(engine.repl.child.before)
            self.restart()
            raise Oct2PyError('Session died, restarting')

        # Read in the output.
        resp = self._reader.read_file(in_file)

        if resp['err']:
            msg = self._parse_error(resp['err'])
            raise Oct2PyError(msg)

        result = resp['result']
        if len(result) == 1:
            result = result[0]
            # Check for sentinel value.
            if isinstance(result, list) and result == ['__no_value__']:
                result = None

        if plot_dir:
            self._engine.make_figures(plot_dir)

        return result

    def _parse_error(self, err):
        """Create a traceback for an Octave evaluation error.
        """
        self.logger.debug(err)
        stack = err['stack']
        if not err['message'].startswith('parse error:'):
            err['message'] = 'error: ' + err['message']
        errmsg = 'Octave evaluation error:\n%s' % err['message']

        if not isinstance(stack, list):
            raise Oct2PyError(errmsg)

        errmsg += '\nerror: called from:'
        for item in stack[:-1]:
            errmsg += '\nerror:   %(name)s at %(line)d' % item
            if 'column' in item:
                errmsg += ', column %(column)s' % item

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
            raise Oct2PyError('Value "%s" does not exist' % name)
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
<<<<<<< HEAD


class _Session(object):

    """Low-level session Octave session interaction.
    """

    def __init__(self, executable, logger=None):
        if executable:
            os.environ['OCTAVE_EXECUTABLE'] = executable
        if 'OCTAVE_EXECUTABLE' not in os.environ and 'OCTAVE' in os.environ:
            os.environ['OCTAVE_EXECUTABLE'] = os.environ['OCTAVE']
        self.engine = OctaveEngine(stdin_handler=self._handle_stdin)
        self.proc = self.engine.repl.child
        self.logger = logger or get_log()
        self._lines = []
        atexit.register(self.close)

    def evaluate(self, cmds, logger=None, out_file='', log=True,
                 timeout=None):
        """Perform the low-level interaction with an Octave Session
        """
        self.logger = logger or self.logger
        engine = self.engine
        self._lines = []

        if not engine:
            raise Oct2PyError('Session Closed, try a restart()')

        if logger and log:
            engine.stream_handler = self._log_line
        else:
            engine.stream_handler = self._lines.append

        engine.eval('clear("ans", "_", "a__");', timeout=timeout)

        for cmd in cmds:
            if cmd:
                try:
                    engine.eval(cmd, timeout=timeout)
                except EOF:
                    self.close()
                    raise Oct2PyError('Session is closed')
        resp = '\n'.join(self._lines).rstrip()

        if 'parse error:' in resp:
            raise Oct2PyError('Syntax Error:\n%s' % resp)

        if 'error:' in resp:
            if len(cmds) == 5:
                main_line = cmds[2].strip()
            else:
                main_line = '\n'.join(cmds)
            msg = ('Oct2Py tried to run:\n"""\n{0}\n"""\n'
                   'Octave returned:\n{1}'
                   .format(cmds[0], resp))
            raise Oct2PyError(msg)

        if out_file:
            save_ans = """
            if exist("ans") == 1,
                _ = ans;
            end,
            if exist("ans") == 1,
                if exist("a__") == 0,
                    save -v6 -mat-binary %(out_file)s _;
                end,
            end;""" % locals()
            engine.eval(save_ans.strip().replace('\n', ''),
                        timeout=timeout)

        return resp

    def handle_plot_settings(self, plot_dir=None, plot_name='plot',
            plot_format='svg', plot_width=None, plot_height=None,
            plot_res=None):
        if not self.engine:
            return
        settings = dict(backend='inline' if plot_dir else 'gnuplot',
                        format=plot_format,
                        name=plot_name,
                        width=plot_width,
                        height=plot_height,
                        resolution=plot_res)
        self.engine.plot_settings = settings

    def extract_figures(self, plot_dir):
        if not self.engine:
            return
        return self.engine.extract_figures(plot_dir)

    def make_figures(self, plot_dir=None):
        if not self.engine:
            return
        return self.engine.make_figures(plot_dir)

    def interrupt(self):
        if not self.engine:
            return
        self.proc.kill(signal.SIGINT)

    def close(self):
        """Cleanly close an Octave session
        """
        if not self.engine:
            return
        proc = self.proc
        try:
            proc.sendline('\nexit')
        except Exception as e:  # pragma: no cover
            self.logger.debug(e)

        try:
            proc.kill(signal.SIGTERM)
            time.sleep(0.1)
            proc.kill(signal.SIGKILL)
        except Exception as e:  # pragma: no cover
            self.logger.debug(e)

        self.proc = None
        self.engine = None

    def _log_line(self, line):
        self._lines.append(line)
        self.logger.debug(line)

    def _handle_stdin(self, line):
        """Handle a stdin request from the session."""
        return input(line.replace(STDIN_PROMPT, ''))

    def __del__(self):
        try:
            self.close()
        except:
            pass

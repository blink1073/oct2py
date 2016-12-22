"""
.. module:: core
   :synopsis: Main module for oct2py package.
              Contains the core session object Oct2Py

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import print_function
import os
import atexit
import signal
import glob
import shutil
import sys
import time
import tempfile

from metakernel.pexpect import TIMEOUT
from octave_kernel.kernel import OctaveEngine

from oct2py.matwrite import MatWrite
from oct2py.matread import MatRead
from oct2py.utils import (
    get_nout, Oct2PyError, get_log, Struct)
from oct2py.compat import unicode, PY2


class Oct2Py(object):

    """Manages an Octave session.

    Uses MAT files to pass data between Octave and Numpy.
    The function must either exist as an m-file in this directory or
    on Octave's path.
    The first command will take about 0.5s for Octave to load up.
    The subsequent commands will be much faster.

    You may provide a logger object for logging events, or the oct2py.get_log()
    default will be used.  Events will be logged as debug unless verbose is set
    when calling a command, then they will be logged as info.

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
        # self.logger.setLevel(logging.DEBUG)
        self._session = None
        self.temp_dir = temp_dir
        self._convert_to_float = convert_to_float
        self.restart()

    @property
    def convert_to_float(self):
        return self._convert_to_float

    @convert_to_float.setter
    def convert_to_float(self, value):
        self._writer.convert_to_float = value
        self._convert_to_float = value

    def __enter__(self):
        """Return octave object, restart session if necessary"""
        if not self._session:
            self.restart()
        return self

    def __exit__(self, type, value, traceback):
        """Close session"""
        self.exit()

    def exit(self):
        """Quits this octave session and removes temp files
        """
        if self._session:
            self._session.close()
        self._session = None

    def push(self, name, var, verbose=False, timeout=None):
        """
        Put a variable or variables into the Octave session.

        Parameters
        ----------
        name : str or list
            Name of the variable(s).
        var : object or list
            The value(s) to pass.
        timeout : float
            Time to wait for response from Octave (per character).

        Examples
        --------
        >>> from oct2py import octave
        >>> y = [1, 2]
        >>> octave.push('y', y)
        >>> octave.pull('y')
        array([[1, 2]])
        >>> octave.push(['x', 'y'], ['spam', [1, 2, 3, 4]])
        >>> octave.pull(['x', 'y'])  # doctest: +SKIP
        [u'spam', array([[1, 2, 3, 4]])]

        Notes
        -----
        Integer type arguments will be converted to floating point
        unless `convert_to_float=False`.

        """
        if isinstance(name, (str, unicode)):
            vars_ = [var]
            names = [name]
        else:
            vars_ = var
            names = name

        for name in names:
            if name.startswith('_'):
                raise Oct2PyError('Invalid name {0}'.format(name))

        try:
            tempdir = tempfile.mkdtemp(dir=self.temp_dir)
            _, load_line = self._writer.create_file(tempdir, vars_, names)
            self._reader.create_file(tempdir)
            self.eval(load_line, verbose=verbose, timeout=timeout)
        finally:
            shutil.rmtree(tempdir, ignore_errors=True)

    def pull(self, var, verbose=False, timeout=None):
        """
        Retrieve a value or values from the Octave session.

        Parameters
        ----------
        var : str or list
            Name of the variable(s) to retrieve.
        timeout : float
            Time to wait for response from Octave (per character).

        Returns
        -------
        out : object
            Object returned by Octave.

        Raises:
          Oct2PyError
            If the variable does not exist in the Octave session.

        Examples:
          >>> from oct2py import octave
          >>> y = [1, 2]
          >>> octave.push('y', y)
          >>> octave.pull('y')
          array([[1, 2]])
          >>> octave.push(['x', 'y'], ['spam', [1, 2, 3, 4]])
          >>> octave.pull(['x', 'y'])  # doctest: +SKIP
          [u'spam', array([[1, 2, 3, 4]])]

        """
        if isinstance(var, (str, unicode)):
            var = [var]
        try:
            temp_dir = tempfile.mkdtemp(dir=self.temp_dir)
            self._reader.create_file(temp_dir)
            argout_list, save_line = self._reader.setup(len(var), var)
            data = self.eval(
                save_line, temp_dir=temp_dir, verbose=verbose, timeout=timeout)
        finally:
            try:
                shutil.rmtree(temp_dir)
            except OSError:
                pass

        if isinstance(data, dict) and not isinstance(data, Struct):
            return [data.get(v, None) for v in argout_list]
        else:
            return data

    def eval(self, cmds, verbose=True, timeout=None, log=True,
             temp_dir=None,
             plot_dir=None, plot_name='plot', plot_format='svg',
             plot_width=None, plot_height=None, return_both=False):
        """
        Evaluate an Octave command or commands.

        Parameters
        ----------
        cmds : str or list
            Commands(s) to pass to Octave.
        verbose : bool, optional
             Log Octave output at INFO level.  If False, log at DEBUG level.
        log : bool, optional
            Whether to log at all.
        timeout : float, optional
            Time to wait for response from Octave (per character).
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
        return_both: bool, optional
            If True, return a (text, value) tuple with the response
            and the return value.

        Returns
        -------
        out : object
            Octave "ans" variable, or None.

        Raises
        ------
        Oct2PyError
            If the command(s) fail.

        """
        if not self._session:
            raise Oct2PyError('No Octave Session')
        if isinstance(cmds, (str, unicode)):
            cmds = [cmds]

        if log:
            [self.logger.debug(line) for line in cmds]

        if timeout is None:
            timeout = self.timeout

        pre_call, post_call = self._get_plot_commands(plot_dir,
                                                      plot_format, plot_width, plot_height,
                                                      plot_name)

        try:
            if not temp_dir:
                temp_dir = tempfile.mkdtemp(dir=self.temp_dir)
                self._reader.create_file(temp_dir)
            try:
                resp = self._session.evaluate(cmds,
                                              logger=self.logger,
                                              log=log,
                                              timeout=timeout,
                                              out_file=self._reader.out_file,
                                              pre_call=pre_call,
                                              post_call=post_call)
            except KeyboardInterrupt:
                self._session.interrupt()
                if os.name == 'nt':
                    self.restart()
                    return 'Octave Session Interrupted, Restarting Session'
                return 'Octave Session Interrupted'
            except TIMEOUT:
                self._session.interrupt()
                raise Oct2PyError('Timed out, interrupting')

            out_file = self._reader.out_file

            data = None
            if os.path.exists(out_file) and os.stat(out_file).st_size:
                try:
                    data = self._reader.extract_file()
                except (TypeError, IOError) as e:
                    self.logger.debug(e)
        finally:
            shutil.rmtree(temp_dir)

        resp = resp.strip()

        if resp:
            if verbose:
                print(resp)
            self.logger.info(resp)

        if return_both:
            return resp, data
        else:
            return data

    def _get_plot_commands(self, plot_dir, plot_format, plot_width,
                           plot_height, plot_name):
        pre_call = ''
        post_call = ''

        spec = '%(plot_dir)s/%(plot_name)s*.%(plot_format)s' % locals()
        existing = glob.glob(spec)
        plot_offset = len(existing)

        if plot_height is None and plot_width is None:
            plot_height = 420
            plot_width = 560
        else:
            if plot_height is None:
                plot_height = 420
            elif plot_width is None:
                plot_width = 560

        pre_call = ''

        if plot_dir is not None:
            pre_call += """
               set(0, 'defaultfigurevisible', 'off');
               graphics_toolkit('gnuplot');
               """
            plot_dir = plot_dir.replace("\\", "/")

            post_call += '''
            _make_figures("%(plot_dir)s", "%(plot_format)s", %(plot_width)s, %(plot_height)s, 0);
        ''' % locals()
        else:
            pre_call += """
            set(0, 'defaultfigurevisible', 'on');
            """

            post_call += """
            drawnow("expose");
            """

        return pre_call.strip(), post_call.strip()

    def restart(self):
        """Restart an Octave session in a clean state
        """
        if self._session:
            self._session.close()
        self._reader = MatRead()
        self._writer = MatWrite(self._oned_as,
                                self._convert_to_float)
        self._session = _Session(self._executable, self.logger)

    # --------------------------------------------------------------
    # Private API
    # --------------------------------------------------------------

    def _make_octave_command(self, name, doc=None):
        """Create a wrapper to an Octave procedure or object

        Adapted from the mlabwrap project

        """
        def octave_command(*args, **kwargs):
            """ Octave command """
            kwargs['nout'] = kwargs.get('nout', get_nout())
            kwargs['verbose'] = kwargs.get('verbose', False)
            return self._call(name, *args, **kwargs)
        # convert to ascii for pydoc
        try:
            doc = doc.encode('ascii', 'replace').decode('ascii')
        except UnicodeDecodeError as e:
            self.logger.debug(e)
        octave_command.__doc__ = "\n" + doc
        octave_command.__name__ = name
        return octave_command

    def _call(self, func, *inputs, **kwargs):
        """
        Oct2Py Parameters
        --------------------------
        inputs : array_like
            Variables to pass to the function.
        verbose : bool, optional
             Log Octave output at INFO level.  If False, log at DEBUG level.
        nout : int, optional
            Number of output arguments.
            This is set automatically based on the number of return values
            requested.
            You can override this behavior by passing a different value.
        timeout : float, optional
            Time to wait for response from Octave (per character).
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
        kwargs : dictionary, optional
            Key - value pairs to be passed as prop - value inputs to the
            function.  The values must be strings or numbers.

        Returns
        -----------
        out : value
            Value returned by the function.

        Raises
        ----------
        Oct2PyError
            If the function call is unsucessful.

        Notes
        -----
        Integer type arguments will be converted to floating point
        unless `convert_to_float=False`.

        """
        nout = kwargs.pop('nout', get_nout())

        argout_list = ['_']

        # these three lines will form the commands sent to Octave
        # load("-v6", "infile", "invar1", ...)
        # [a, b, c] = foo(A, B, C)
        # save("-v6", "out_file", "outvar1", ...)
        load_line = call_line = save_line = ''

        prop_vals = []
        eval_kwargs = {}
        for (key, value) in kwargs.items():
            if key in ['verbose', 'timeout'] or key.startswith('plot_'):
                eval_kwargs[key] = value
                continue
            if isinstance(value, (str, unicode, int, float)):
                prop_vals.append('"%s", %s' % (key, repr(value)))
            else:
                msg = 'Keyword arguments must be a string or number: '
                msg += '%s = %s' % (key, value)
                raise Oct2PyError(msg)
        prop_vals = ', '.join(prop_vals)

        try:
            temp_dir = tempfile.mkdtemp(dir=self.temp_dir)
            self._reader.create_file(temp_dir)
            if nout:
                # create a dummy list of var names ("a", "b", "c", ...)
                # use ascii char codes so we can increment
                argout_list, save_line = self._reader.setup(nout)
                call_line = '[{0}] = '.format(', '.join(argout_list))

            call_line += func + '('

            if inputs:
                argin_list, load_line = self._writer.create_file(
                    temp_dir, inputs)
                call_line += ', '.join(argin_list)

            if prop_vals:
                if inputs:
                    call_line += ', '
                call_line += prop_vals

            call_line += ');'

            # create the command and execute in octave
            cmd = [load_line, call_line, save_line]
            data = self.eval(cmd, temp_dir=temp_dir, **eval_kwargs)
        finally:
            try:
                shutil.rmtree(temp_dir)
            except OSError:
                pass

        if isinstance(data, dict) and not isinstance(data, Struct):
            data = [data.get(v, None) for v in argout_list]
            if len(data) == 1 and data.values()[0] is None:
                data = None

        return data

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
           If the procedure or object does not exist.

        """
        if name == 'keyboard':
            return 'Built-in Function: keyboard ()'
        exist = self.eval('exist {0}'.format(name), log=False,
                          verbose=False)
        if exist == 0:
            msg = 'Name: "%s" does not exist on the Octave session path'
            raise Oct2PyError(msg % name)
        doc = 'No documentation for %s' % name

        try:
            doc, _ = self.eval('help {0}'.format(name), log=False,
                               verbose=False, return_both=True)
        except Oct2PyError as e:
            if 'syntax error' in str(e):
                raise(e)
            doc, _ = self.eval('type("{0}")'.format(name), log=False,
                               verbose=False, return_both=True)
            if isinstance(doc, list):
                doc = doc[0]
            doc = '\n'.join(doc.splitlines()[:3])

        default = self._call.__doc__
        doc += '\n' + '\n'.join([line[8:] for line in default.splitlines()])

        return doc

    def __getattr__(self, attr):
        """Automatically creates a wapper to an Octave function or object.

        Adapted from the mlabwrap project.

        """
        # needed for help(Oct2Py())
        if attr == '__name__':
            return super(Oct2Py, self).__getattr__(attr)
        elif attr == '__file__':
            return __file__
        # close_ -> close
        if attr[-1] == "_":
            name = attr[:-1]
        else:
            name = attr
        doc = self._get_doc(name)
        octave_command = self._make_octave_command(name, doc)
        #!!! attr, *not* name, because we might have python keyword name!
        setattr(self, attr, octave_command)
        return octave_command


class _Session(object):

    """Low-level session Octave session interaction.
    """

    def __init__(self, executable, logger=None):
        if executable:
            os.environ['OCTAVE_EXECUTABLE'] = executable
        if 'OCTAVE_EXECUTABLE' not in os.environ and 'OCTAVE' in os.environ:
            os.environ['OCTAVE_EXECUTABLE'] = os.environ['OCTAVE']
        self.engine = OctaveEngine()
        self.stdout = sys.stdout
        self.proc = self.engine.repl.child
        self.logger = logger or get_log()
        atexit.register(self.close)

    def evaluate(self, cmds, logger=None, out_file='', log=True,
                 timeout=None, pre_call='', post_call=''):
        """Perform the low-level interaction with an Octave Session
        """
        self.logger = logger or self.logger
        proc = self.proc

        if not self.proc:
            raise Oct2PyError('Session Closed, try a restart()')

        expr = '\n'.join(cmds)

        # use ascii code 2 for start of text, 3 for end of text, and
        # 24 to signal an error
        output = """
        %(pre_call)s

        clear("ans");
        rehash;
        clear("_");
        clear("a__");
        disp(char(2));

        try
            disp(char(2));
            %(expr)s
            if exist("ans") == 1
               _ = ans;
            end
            disp(char(3))

        catch
            disp(lasterr());
            disp(char(24));
        end

        if exist("_") == 1
            if exist("a__") == 0
                save -v6 -mat-binary %(out_file)s _;
            end
        end

        %(post_call)s

        disp(char(3))
        """ % locals()

        if len(cmds) == 5:
            main_line = cmds[2].strip()
        else:
            main_line = '\n'.join(cmds)

        if 'keyboard' in expr:
            proc.sendline('keyboard')
            self.interact()
            return ''

        proc.sendline(output)

        # Run the pre-call
        proc.expect(chr(2), timeout=timeout)

        # Try and start the eval
        proc.expect('%s|error: |parse error:' % chr(2), timeout=timeout)
        resp = proc.before + proc.after

        if 'parse error:' in resp:
            resp = [resp[resp.index('parse error:'):]]
        elif 'error:' in resp:
            resp = [resp[resp.index('error:'):]]
        else:
            resp = []

        while 1:
            line = self.readline(timeout)

            if chr(3) in line:
                break

            elif chr(24) in line:
                msg = ('Oct2Py tried to run:\n"""\n{0}\n"""\n'
                       'Octave returned:\n{1}'
                       .format(main_line, '\n'.join(resp)))
                proc.expect(chr(3), timeout=timeout)
                raise Oct2PyError(msg)

            elif '\x1b[C' in line or line.strip() == '>>':
                line = ''

            elif line.endswith('> ') and not line.endswith('>>> '):
                self.interact(line)

            elif line.startswith(' ') and line.strip() == '^':
                raise Oct2PyError('Syntax Error:\n%s' % '\n'.join(resp))

            elif logger and log:
                logger.debug(line)

            if resp or line:
                resp.append(line)

        # Run the post-call
        proc.expect('%s|error: |parse error:' % chr(3), timeout=timeout)
        post = proc.before + proc.after
        if (chr(3)) not in post:
            post += self.readline(timeout)
            raise Oct2PyError('Error in post_call: %s' % post)

        return '\n'.join(resp).rstrip()

    def readline(self, timeout=None):
        proc = self.proc
        proc.expect([proc.crlf, proc.delimiter], timeout=timeout)
        return proc.before

    def interrupt(self):
        if os.name == 'nt':
            self.close()
        else:
            self.proc.kill(signal.SIGINT)

    def interact(self, prompt='debug> '):
        """Manage an Octave Debug Prompt interaction"""
        msg = 'Entering Octave Debug Prompt...\n%s' % prompt
        self.stdout.write(msg)
        proc = self.proc
        while 1:
            inp_func = input if not PY2 else raw_input
            try:
                inp = inp_func() + '\n'
            except EOFError:
                return
            if inp in ['exit\n', 'quit\n', 'dbcont\n', 'dbquit\n',
                       'exit()\n', 'quit()\n']:
                inp = 'return\n'
            proc.write('disp(char(3));' + inp)
            if inp == 'return\n':
                proc.sendline('return')
                proc.sendline('clear _')
                return
            proc.expect('\x03')
            proc.expect(prompt)
            self.stdout.write(proc.before + proc.after)

    def close(self):
        """Cleanly close an Octave session
        """
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

    def __del__(self):
        try:
            self.close()
        except:
            pass

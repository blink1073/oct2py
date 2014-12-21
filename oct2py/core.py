"""
.. module:: core
   :synopsis: Main module for oct2py package.
              Contains the core session object Oct2Py

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from __future__ import print_function
import os
import re
import atexit
import signal
import glob
import logging
import subprocess
import sys
import threading
import time
from tempfile import gettempdir
import warnings
try:
    import pty
except ImportError:
    pty = None

from oct2py.matwrite import MatWrite
from oct2py.matread import MatRead
from oct2py.utils import (
    get_nout, Oct2PyError, get_log, Struct, _remove_temp_files)
from oct2py.compat import unicode, PY2, queue


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
        Name of the Octave executable, can be a system path.
    logger : logging object, optional
        Optional logger to use for Oct2Py session
    timeout : float, opional
        Timeout in seconds for commands
    oned_as : {'row', 'column'}, optional
        If 'column', write 1-D numpy arrays as column vectors.
        If 'row', write 1-D numpy arrays as row vectors.}
    temp_dir : str, optional
        If specified, the session's MAT files will be created in the
        directory, otherwise a default directory is used.  This can be
        a shared memory (tmpfs) path.
    """

    def __init__(self, executable=None, logger=None, timeout=None,
                 oned_as='row', temp_dir=None):
        """Start Octave and set up the session.
        """
        self._oned_as = oned_as
        self._temp_dir = temp_dir or gettempdir()
        self._executable = executable
        atexit.register(lambda: _remove_temp_files(self._temp_dir))

        self.timeout = timeout
        if not logger is None:
            self.logger = logger
        else:
            self.logger = get_log()
        #self.logger.setLevel(logging.DEBUG)
        self._session = None
        self.restart()

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
        try:
            self._writer.remove_file()
            self._reader.remove_file()
        except Oct2PyError:
            pass

    def push(self, name, var, verbose=False, timeout=None):
        """
        Put a variable or variables into the Scilab session.

        Parameters
        ----------
        name : str or list
            Name of the variable(s).
        var : object or list
            The value(s) to pass.
        timeout : float
            Time to wait for response from Scilab (per character).

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
        _, load_line = self._writer.create_file(vars_, names)
        self.eval(load_line, verbose=verbose, timeout=timeout)

    def pull(self, var, verbose=False, timeout=None):
        """
        Retrieve a value or values from the Scilab session.

        Parameters
        ----------
        var : str or list
            Name of the variable(s) to retrieve.
        timeout : float
            Time to wait for response from Scilab (per character).

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
        argout_list, save_line = self._reader.setup(len(var), var)
        data = self.eval(
            save_line, verbose=verbose, timeout=timeout)
        if isinstance(data, dict) and not isinstance(data, Struct):
            return [data.get(v, None) for v in argout_list]
        else:
            return data

    def eval(self, cmds, verbose=True, timeout=None, log=True,
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
            resp = self._session.evaluate(cmds,
                                          logger=self.logger,
                                          log=log,
                                          timeout=timeout,
                                          pre_call=pre_call,
                                          post_call=post_call)
        except KeyboardInterrupt:
            self._session.interrupt()
            if os.name == 'nt':
                self.restart()
                return 'Octave Session Interrupted, Restarting Session'
            return 'Octave Session Interrupted'

        outfile = self._reader.out_file

        data = None
        if os.path.exists(outfile) and os.stat(outfile).st_size:
            try:
                data = self._reader.extract_file()
            except (TypeError, IOError) as e:
                self.logger.debug(e)

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

        if not plot_height is None or not plot_width is None:
            pre_call += """
            close all;
            """

        if plot_height is None and plot_width is None:
            plot_height = 420
            plot_width = 560
        else:
            if plot_height is None:
                plot_height = 420
            elif plot_width is None:
                plot_width = 560

        pre_call += """
            set(0, 'DefaultFigurePosition', [300, 200, %(plot_width)s, %(plot_height)s]);
            __oct2py_figures = [];
            """ % locals()

        if not plot_dir is None:

            pre_call += """
                close all;
             __oct2py_figure_visible = 'off';
               """

            plot_dir = plot_dir.replace("\\", "/")

            post_call += '''
        for f = __oct2py_figures
          outfile = sprintf('%(plot_dir)s/%(plot_name)s%%03d.%(plot_format)s', f + %(plot_offset)s);
          p = get(f, 'position');
          w = %(plot_width)s;
          h = %(plot_height)s;
          if p(3) > %(plot_width)s
                h = p(4) * w / p(3);
          end
          if p(4) > %(plot_height)s
                w = p(3) * h / p(4);
          end
          size_fmt = sprintf('-S%%d,%%d', w, h);
          try
            print(f, outfile, '-d%(plot_format)s', '-tight', size_fmt);
          end
        end
        close('all');
        ''' % locals()
        else:
            pre_call += """
             __oct2py_figure_visible = 'on';
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
        self._reader = MatRead(self._temp_dir)
        self._writer = MatWrite(self._temp_dir, self._oned_as)
        self._session = _Session(self._executable,
                                 self._reader.out_file, self.logger)

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
            if not 'Built-in Function' in doc:
                self.eval('clear {0}'.format(name), log=False, verbose=False)
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
        """
        nout = kwargs.pop('nout', get_nout())

        argout_list = ['_']

        # these three lines will form the commands sent to Octave
        # load("-v6", "infile", "invar1", ...)
        # [a, b, c] = foo(A, B, C)
        # save("-v6", "outfile", "outvar1", ...)
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

        if nout:
            # create a dummy list of var names ("a", "b", "c", ...)
            # use ascii char codes so we can increment
            argout_list, save_line = self._reader.setup(nout)
            call_line = '[{0}] = '.format(', '.join(argout_list))

        call_line += func + '('

        if inputs:
            argin_list, load_line = self._writer.create_file(inputs)
            call_line += ', '.join(argin_list)

        if prop_vals:
            if inputs:
                call_line += ', '
            call_line += prop_vals

        call_line += ')'

        # create the command and execute in octave
        cmd = [load_line, call_line, save_line]
        data = self.eval(cmd, **eval_kwargs)

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


class _Reader(object):

    """Read characters from an Octave session in a thread.
    """

    def __init__(self, fid, queue):
        self.fid = fid
        self.queue = queue
        self.thread = threading.Thread(target=self.read_incoming)
        self.thread.setDaemon(True)
        self.thread.start()

    def read_incoming(self):
        """"Read text a chunk at a time, parsing into lines
        and putting them in the queue.
        If there is a line with only a ">" char, put that on the queue
        """
        buf = ''
        debug_prompt = re.compile(r'\A[\w]+>>? ')
        while 1:
            try:
                buf += os.read(self.fid, 1024).decode('utf8', 'replace')
            except:
                self.queue.put(None)
                return
            lines = buf.splitlines()
            for line in lines[:-1]:
                self.queue.put(line)
            if buf.endswith('\n'):
                self.queue.put(lines[-1])
                buf = ''
            elif re.match(debug_prompt, lines[-1]):
                self.queue.put(lines[-1])
                buf = ''
            else:
                buf = lines[-1]


class _Session(object):

    """Low-level session Octave session interaction.
    """

    def __init__(self, executable, outfile, logger):
        self.timeout = int(1e6)
        self.read_queue = queue.Queue()
        self.proc = self.start(executable)
        self.stdout = sys.stdout
        self.outfile = outfile
        self.logger = logger
        self.first_run = True
        self.set_timeout()
        atexit.register(self.close)

    def start(self, executable):
        """
        Start an Octave session in a subprocess.

        Parameters
        ==========
        executable : str
            Name or path to Scilab process.

        Returns
        =======
        out : fid
            File descriptor for the Octave subprocess

        Raises
        ======
        Oct2PyError
            If the session is not opened sucessfully.

        Notes
        =====
        Options sent to Octave: -q is quiet startup, --braindead is
        Matlab compatibilty mode.

        """
        errmsg = ('\n\n`octave` not found.  Please see documentation at:\n'
                  'http://blink1073.github.io/oct2py/source/installation.html')
        ON_POSIX = 'posix' in sys.builtin_module_names
        if pty:
            master, slave = pty.openpty()
            self.wfid, self.rfid = master, master
            rpipe, wpipe = slave, slave
        else:
            self.rfid, wpipe = os.pipe()
            rpipe, self.wfid = os.pipe()

        kwargs = dict(close_fds=ON_POSIX, bufsize=0, stdin=rpipe,
                      stderr=wpipe, stdout=wpipe)

        if not executable:
            executable = 'octave'

        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs['startupinfo'] = startupinfo
            kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

        try:
            proc = subprocess.Popen([executable, '-q', '--braindead'],
                                    **kwargs)

        except OSError:  # pragma: no cover
            raise Oct2PyError(errmsg)

        else:
            self.reader = _Reader(self.rfid, self.read_queue)
            return proc

    def set_timeout(self, timeout=None):
        if timeout is None:
            timeout = int(1e6)
        self.timeout = timeout

    def evaluate(self, cmds, logger=None, log=True,
                 timeout=None, pre_call='', post_call=''):
        """Perform the low-level interaction with an Octave Session
        """
        self.logger = logger

        self.set_timeout(timeout)

        if not self.proc:
            raise Oct2PyError('Session Closed, try a restart()')

        if os.path.exists(self.outfile):
            try:
                os.remove(self.outfile)
            except OSError as e:
                self.logger.debug(e)

        expr = '\n'.join(cmds)

        if self.first_run:
            self._handle_first_run()

        outfile = self.outfile

        # use ascii code 2 for start of text, 3 for end of text, and
        # 24 to signal an error
        output = """
        %(pre_call)s

        clear("ans");
        clear("_");
        clear("a__");
        disp(char(2))

        try
           set(0, 'DefaultFigureCreateFcn', @fig_create)
        end

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
                save -v6 %(outfile)s _;
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
            self.write('keyboard\n')
            self.interact()
            return ''

        self.write(output + '\n')

        self.expect(chr(2))

        resp = self.expect('%s|error: |parse error:' % chr(2))

        if 'parse error:' in resp:
            resp = [resp[resp.index('parse error:'):]]
        elif 'error:' in resp:
            resp = [resp[resp.index('error:'):]]
        else:
            resp = []

        while 1:
            line = self.readline()

            if chr(3) in line:
                break

            elif chr(24) in line:
                msg = ('Oct2Py tried to run:\n"""\n{0}\n"""\n'
                       'Octave returned:\n{1}'
                       .format(main_line, '\n'.join(resp)))
                self.expect(chr(3))
                raise Oct2PyError(msg)

            elif '\x1b[C' in line or line.strip() == '>>':
                line = ''

            elif line.endswith('> '):
                self.interact(line)

            elif line.startswith(' ') and line.strip() == '^':
                if sys.platform == 'win32':
                    self.close()
                raise Oct2PyError('Syntax Error:\n%s' % '\n'.join(resp))

            elif logger and log:
                logger.debug(line)

            if resp or line:
                resp.append(line)

        self.expect(chr(3))

        return '\n'.join(resp).rstrip()

    def _handle_first_run(self):
        self.write('disp(available_graphics_toolkits());disp(char(3))\n')
        resp = self.expect(chr(3))
        if not os.name == 'nt':
            try:
                subprocess.check_output('which gnuplot', shell=True)
            except subprocess.CalledProcessError:
                resp = None

        if resp:
            self.write("graphics_toolkit('gnuplot')\n")
        else:
            warnings.warn('Oct2Py may not be able to display plots '
               'properly without gnuplot, please install it '
               '(gnuplot-x11 on Linux)')

        self.first_run = False
        self.write("""
             global __oct2py_figures = [];
             global __oct2py_figure_visible = 'on';
                function fig_create(src, event);
                  global __oct2py_figures;
                  global __oct2py_figure_visible;
                  set(src, 'visible', __oct2py_figure_visible);
                  __oct2py_figures(end + 1) = src;
                end;\n""")

    def interrupt(self):
        if os.name == 'nt':
            self.close()
        else:
            self.proc.send_signal(signal.SIGINT)

    def expect(self, strings):
        """Look for a string or strings in the incoming data"""
        if not isinstance(strings, list):
            strings = [strings]
        lines = []
        while 1:
            line = self.readline()
            lines.append(line)
            if line:
                for string in strings:
                    if re.search(string, line):
                        return '\n'.join(lines)

    def readline(self):
        t0 = time.time()
        while 1:
            try:
                val = self.read_queue.get_nowait()
            except queue.Empty:
                pass
            else:
                if val is None:
                    self.close()
                    return
                else:
                    return val
            time.sleep(1e-6)
            if (time.time() - t0) > self.timeout:
                self.interrupt()
                raise Oct2PyError('Timed out, interrupting')

    def write(self, message):
        """Write a message to the process using utf-8 encoding"""
        os.write(self.wfid, message.encode('utf-8'))

    def interact(self, prompt='debug> '):
        """Manage an Octave Debug Prompt interaction"""
        msg = 'Entering Octave Debug Prompt...\n%s' % prompt
        self.stdout.write(msg)
        while 1:
            inp_func = input if not PY2 else raw_input
            try:
                inp = inp_func() + '\n'
            except EOFError:
                return
            if inp in ['exit\n', 'quit\n', 'dbcont\n', 'dbquit\n',
                       'exit()\n', 'quit()\n']:
                inp = 'return\n'
            self.write('disp(char(3));' + inp)
            if inp == 'return\n':
                self.write('return\n')
                self.write('clear _\n')
                return
            self.expect('\x03')
            self.stdout.write(self.expect(prompt))

    def close(self):
        """Cleanly close an Octave session
        """
        try:
            self.write('\nexit\n')
        except Exception as e:  # pragma: no cover
            self.logger.debug(e)

        try:
            self.proc.terminate()
            time.sleep(0.1)
            self.proc.kill()
        except Exception as e:  # pragma: no cover
            self.logger.debug(e)

        self.proc = None

    def __del__(self):
        try:
            self.close()
        except:
            pass

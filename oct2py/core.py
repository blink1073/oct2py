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
import subprocess
import sys
import threading
import time
from tempfile import gettempdir
import warnings
import ctypes

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

    def __init__(self, logger=None, timeout=-1, oned_as='row',
                 temp_dir=None):
        """Start Octave and set up the session.
        """
        self._oned_as = oned_as
        self._temp_dir = temp_dir or gettempdir()
        atexit.register(lambda: _remove_temp_files(self._temp_dir))

        self.timeout = timeout
        if not logger is None:
            self.logger = logger
        else:
            self.logger = get_log()
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

    def push(self, name, var, verbose=False, timeout=-1):
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

    def pull(self, var, verbose=False, timeout=-1):
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
        data = self.eval(save_line, verbose=verbose, timeout=timeout)
        if isinstance(data, dict) and not isinstance(data, Struct):
            return [data.get(v, None) for v in argout_list]
        else:
            return data

    def eval(self, cmds, verbose=False, log=True, timeout=-1):
        """
        Evaluate an Octave command or commands.

        Parameters
        ----------
        cmds : str or list
            Commands(s) to pass to Octave.
        verbose : bool, optional
             Log Octave output at info level.
        timeout : float, optional
            Time to wait for response from Octave (per character).

        Returns
        -------
        out : str
            Results printed by Octave.

        Raises
        ------
        Oct2PyError
            If the command(s) fail.

        """
        if not self._session:
            raise Oct2PyError('No Octave Session')
        if isinstance(cmds, (str, unicode)):
            cmds = [cmds]

        if verbose and log:
            [self.logger.info(line) for line in cmds]
        elif log:
            [self.logger.debug(line) for line in cmds]
        if timeout == -1:
            timeout = self.timeout

        post_call = ''
        for cmd in cmds:

            if cmd.strip() == 'clear':
                continue

            match = re.match('([a-z][a-zA-Z0-9_]*) *=', cmd)
            if match and not cmd.strip().endswith(';'):
                post_call = 'ans = %s' % match.groups()[0]
                break

            match = re.match('([a-z][a-zA-Z0-9_]*)\Z', cmd.strip())
            if match and not cmd.strip().endswith(';'):
                post_call = 'ans = %s' % match.groups()[0]
                break

        cmds.append(post_call)

        try:
            resp = self._session.evaluate(cmds, verbose, log, self.logger,
                                          timeout=timeout)
        except KeyboardInterrupt:
            self._session.interrupt()
            return 'Octave Session Interrupted'

        outfile = self._reader.out_file
        if os.path.exists(outfile) and os.stat(outfile).st_size:
            try:
                return self._reader.extract_file()
            except (TypeError, IOError) as e:
                self.logger.debug(e)

        if resp:
            return resp

    def restart(self):
        """Restart an Octave session in a clean state
        """
        self._reader = MatRead(self._temp_dir)
        self._writer = MatWrite(self._temp_dir, self._oned_as)
        self._session = _Session(self._reader.out_file, self.logger)

    # --------------------------------------------------------------
    # Private API
    # --------------------------------------------------------------

    def _make_octave_command(self, name, doc=None):
        """Create a wrapper to an Octave procedure or object

        Adapted from the mlabwrap project

        """
        def octave_command(*args, **kwargs):
            """ Octave command """
            kwargs['nout'] = get_nout()
            kwargs['verbose'] = kwargs.get('verbose', False)
            if not 'Built-in Function' in doc:
                self.eval('clear {0}'.format(name), log=False, verbose=False)
            kwargs['command'] = True
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
        Call an Octave function with optional arguments.

        This is a low-level command used by dynamic functions.

        Parameters
        ----------
        func : str
            Function name to call.
        inputs : array_like
            Variables to pass to the function.
        nout : int, optional
            Number of output arguments.
            This is set automatically based on the number of
            return values requested (see example below).
            You can override this behavior by passing a
            different value.
        verbose : bool, optional
             Log Octave output at info level.

        Returns
        -------
        out : str or tuple
            If nout > 0, returns the values from Octave as a tuple.
            Otherwise, returns the output displayed by Octave.

        Raises
        ------
        Oct2PyError
            If the call is unsucessful.

        """
        verbose = kwargs.get('verbose', False)
        nout = kwargs.get('nout', get_nout())
        timeout = kwargs.get('timeout', self.timeout)
        argout_list = ['_']

        # these three lines will form the commands sent to Octave
        # load("-v6", "infile", "invar1", ...)
        # [a, b, c] = foo(A, B, C)
        # save("-v6", "outfile", "outvar1", ...)
        load_line = call_line = save_line = ''

        if nout:
            # create a dummy list of var names ("a", "b", "c", ...)
            # use ascii char codes so we can increment
            argout_list, save_line = self._reader.setup(nout)
            call_line = '[{0}] = '.format(', '.join(argout_list))
        if inputs:
            argin_list, load_line = self._writer.create_file(inputs)
            call_line += '{0}({1})'.format(func, ', '.join(argin_list))
        elif nout and not '(' in func:
            # call foo() - no arguments
            call_line += '{0}()'.format(func)
        else:
            # run foo
            call_line += '{0}'.format(func)

        if not '__ipy_figures' in func:
            if not call_line.endswith(')') and nout:
                call_line += '()'

        # create the command and execute in octave
        cmd = [load_line, call_line, save_line]
        data = self.eval(cmd, verbose=verbose, timeout=timeout)

        if isinstance(data, dict) and not isinstance(data, Struct):
            data = [data.get(v, None) for v in argout_list]
            if len(data) == 1 and data[0] is None:
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
            doc = self.eval('help {0}'.format(name), log=False,
                            verbose=False)
        except Oct2PyError as e:
            if 'syntax error' in str(e):
                raise(e)
            try:
                doc = self.eval('x = type("{0}")'.format(name), log=False,
                                verbose=False)
                if isinstance(doc, list):
                    doc = doc[0]
                doc = '\n'.join(doc.splitlines()[:3])
            except Oct2PyError as e:
                self.logger.debug(e)
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
                buf += os.read(self.fid, 1024).decode('utf8')
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

    def __init__(self, outfile, logger):
        self.timeout = int(1e6)
        self.read_queue = queue.Queue()
        self.proc = self.start()
        self.stdout = sys.stdout
        self.outfile = outfile
        self.logger = logger
        self.first_run = True
        self.set_timeout()
        atexit.register(self.close)

    def start(self):
        """
        Start an octave session in a subprocess.

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
        return self.start_subprocess()

    def start_subprocess(self):
        """Start octave using a subprocess (no tty support)"""
        errmsg = ('\n\nPlease install GNU Octave and put it in your path\n')
        ON_POSIX = 'posix' in sys.builtin_module_names
        self.rfid, wpipe = os.pipe()
        rpipe, self.wfid = os.pipe()
        kwargs = dict(close_fds=ON_POSIX, bufsize=0, stdin=rpipe,
                      stderr=wpipe, stdout=wpipe)
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs['startupinfo'] = startupinfo
            kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            proc = subprocess.Popen(['octave', '-q', '--braindead'],
                                    **kwargs)
        except OSError:  # pragma: no cover
            raise Oct2PyError(errmsg)
        else:
            self.reader = _Reader(self.rfid, self.read_queue)
            return proc

    def set_timeout(self, timeout=-1):
        if timeout == -1:
            timeout = int(1e6)
        self.timeout = timeout

    def evaluate(self, cmds, verbose=True, log=True, logger=None, timeout=-1):
        """Perform the low-level interaction with an Octave Session
        """
        self.logger = logger

        if not timeout == -1:
            self.set_timeout(timeout)

        if not self.proc:
            raise Oct2PyError('Session Closed, try a restart()')

        if os.path.exists(self.outfile):
            try:
                os.remove(self.outfile)
            except OSError as e:
                self.logger.debug(e)

        # use ascii code 2 for start of text, 3 for end of text, and
        # 24 to signal an error
        exprs = []
        for cmd in cmds:
            cmd = cmd.strip().replace('\n', ';')
            cmd = re.sub(';\s*;', ';', cmd)
            cmd = cmd.replace('"', '""')
            subcmds = cmd.split(';')
            for sub in subcmds:
                if sub.replace(';', '') and not sub.startswith(('%', '#')):
                    exprs.append(sub)

        if self.first_run:
            self._handle_first_run()

        if '__inline=1;' in ';'.join(exprs):
            visible = "off"
        else:
            visible = "on"

        fig_handler = """
        global __oct2py_figures = [];
        function fig_create(src, event)
          global __oct2py_figures
          set(src, 'visible', '%s');
          __oct2py_figures(size(__oct2py_figures) + 1) = src;
        end
        set(0, 'DefaultFigureCreateFcn', @fig_create)""" % visible

        exprs = fig_handler.strip().splitlines() + exprs

        expr = ';'.join(exprs)

        self.logger.debug(expr)

        output = """
        clear("ans");
        clear("a__");
        disp(char(2));

        eval("%s", "failed = 1;")
        if exist("failed") == 1 && failed
            disp(lasterr())
            disp(char(24))
        else
            if exist("ans") == 1
                _ = ans;
                if exist("a__") == 0
                    save -v6 %s _;
                end
            end
            disp(char(3))
        end
        drawnow("expose");
        clear("failed")
        """ % (expr, self.outfile)

        if len(cmds) == 5:
            main_line = cmds[2].strip()
        else:
            main_line = '\n'.join(cmds)

        if 'keyboard' in output:
            self.write('keyboard\n')
            self.interact()
            return

        self.write(output + '\n')

        self.expect(chr(2))

        resp = []
        while 1:
            line = self.readline()

            if chr(3) in line:
                break

            elif chr(24) in line:
                msg = ('Oct2Py tried to run:\n"""\n{0}\n"""\n'
                       'Octave returned:\n{1}'
                       .format(main_line, '\n'.join(resp)))
                raise Oct2PyError(msg)

            elif line.endswith('> '):
                self.interact(line)

            if verbose and logger:
                logger.info(line)

            elif log and logger:
                logger.debug(line)

            if resp or line:
                resp.append(line)

        return '\n'.join(resp).rstrip()

    def _handle_first_run(self):
        self.write('disp(available_graphics_toolkits());disp(char(3))\n')
        resp = self.expect(chr(3))
        if not 'gnuplot' in resp:
            warnings.warn('Oct2Py will not be able to display plots '
                          'properly without gnuplot, please install it '
                          '(gnuplot-x11 on Linux)')
        else:
            self.write("graphics_toolkit('gnuplot')\n")
        self.first_run = False

    def interrupt(self):
        if os.name == 'nt':
            CTRL_BREAK_EVENT = 1
            interrupt = ctypes.windll.kernel32.GenerateConsoleCtrlEvent
            interrupt(CTRL_BREAK_EVENT, self.proc.pid)
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
        except Exception as e:  # pragma: no cover
            self.logger.debug(e)

        self.proc = None

    def __del__(self):
        try:
            self.close()
        except:
            pass

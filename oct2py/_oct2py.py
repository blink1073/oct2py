"""
.. module:: _oct2py
   :synopsis: Main module for oct2py package.
              Contains the Octave session object Oct2Py

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
import os
import re
import atexit
import doctest
import logging
from ._matwrite import MatWrite
from ._matread import MatRead
from ._utils import _open, _get_nout, Oct2PyError, _remove_temp_files


class Oct2Py(object):
    """Manages an Octave session.

    Uses MAT files to pass data between Octave and Numpy.
    The function must either exist as an m-file in this directory or
    on Octave's path.
    The first command will take about 0.5s for Octave to load up.
    The subsequent commands will be much faster.
    Plotting commands within an m-file do not work unless you add this
    after every plot line::

       ;figure(gcf() + 1);

    """
    def __init__(self, logger=None):
        """Start Octave and create our MAT helpers
        """
        if not logger is None:
            self.logger = logger
        else:
            self.logger = logging.getLogger('oct2py')
            self.logger.setLevel(logging.INFO)
        self.restart()
        
    def __enter__(self):
        '''Return octave object, restart session if necessary'''
        if not self._session:
            self.restart()
        return self
    
    def __exit__(self, type, value, traceback):
        '''Close session'''
        self.close()

    def close(self, handle=None):
        """Closes this octave session and removes temp files
        """
        if self._isopen:
            self._isopen = False
        else:
            return
        if not handle:
            handle = self._session
            self._session = None
        # Send the terminate signal to all the process groups
        try:
            handle.stdout.write('exit\n')
        except IOError:
            pass
        try:
            handle.terminate()
        except OSError:
            pass
        _remove_temp_files()

    def _close(self, handle=None):
        '''Depracated, call close instead
        '''
        self.close(handle)

    def run(self, script, **kwargs):
        """
        Run artibrary Octave code.

        Parameters
        -----------
        script : str
            Command script to send to Octave for execution.
        verbose : bool, optional
            Print Octave output.

        Returns
        -------
        out : str
            Octave printed output.

        Raises
        ------
        Oct2PyError
            If the script cannot be run by Octave.

        Examples
        --------
        >>> from oct2py import octave
        >>> out = octave.run('y=ones(3,3)')
        >>> print(out)
        y =
        <BLANKLINE>
                1        1        1
                1        1        1
                1        1        1
        <BLANKLINE>
        >>> octave.run('x = mean([[1, 2], [3, 4]])')
        u'x =  2.5000'

        """
        # don't return a value from a script
        kwargs['nout'] = 0
        # this line is needed to force the plot to display
        for cmd in ['gplot', 'plot', 'bar', 'contour', 'hist', 'loglog',
                    'polar', 'semilogx', 'stairs', 'gsplot', 'mesh',
                    'meshdom']:
            if cmd + '(' in script:
                self._set_graphics_toolkit()
                script += ";figure(gcf() + 1);"
        return self.call(script, **kwargs)

    def call(self, func, *inputs, **kwargs):
        """
        Call am Octave function with optional arguments.

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
            Print Octave output.

        Returns
        -------
        out : str or tuple
            If nout > 0, returns the values from Octave as a tuple.
            Otherwise, returns the output displayed by Octave.

        Raises
        ------
        Oct2PyError
            If the call is unsucessful.

        Examples
        --------
        >>> from oct2py import octave
        >>> b = octave.call('ones', 1, 2)
        >>> print(b)
        [ 1.  1.]
        >>> x, y = 1, 2
        >>> a = octave.call('zeros', x, y, verbose=True)
        a__ =
        <BLANKLINE>
                0        0
        <BLANKLINE>
        >>> U, S, V = octave.call('svd', [[1, 2], [1, 3]])
        >>> print(U, S, V)
        (array([[-0.57604844, -0.81741556],
               [-0.81741556,  0.57604844]]), array([[ 3.86432845,  0.        ],
               [ 0.        ,  0.25877718]]), array([[-0.36059668, -0.93272184],
               [-0.93272184,  0.36059668]]))

        """
        verbose = kwargs.get('verbose', False)
        nout = kwargs.get('nout', _get_nout())

        # handle references to script names - and paths to them
        if func.endswith('.m'):
            if os.path.dirname(func):
                self.addpath(os.path.dirname(func))
                func = os.path.basename(func)
            func = func[:-2]

        if not self._writer.dummy_cell:
            self._get_dummy_cell()

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
        elif nout:
            # call foo() - no arguments
            call_line += '{0}()'.format(func)
        else:
            # run foo
            call_line += '{0}'.format(func)
        # A special command is needed to force the plot to display
        if func in ['gplot', 'plot', 'bar', 'contour', 'hist', 'loglog',
                    'polar', 'semilogx', 'semilogy', 'stairs', 'gsplot',
                    'mesh', 'meshdom', 'meshc', 'surf', 'plot3', 'meshz',
                    'surfc', 'surfl', 'surfnorm', 'diffuse', 'specular',
                    'ribbon', 'scatter3']:
            self._set_graphics_toolkit()
            call_line += ";figure(gcf() + 1);"

        # create the command and execute in octave
        cmd = [load_line, call_line, save_line]
        resp = self._eval(cmd, verbose=verbose)

        if nout:
            return self._reader.extract_file(argout_list)
        else:
            return resp

    def put(self, names, var):
        """
        Put a variable into the Octave session.

        Parameters
        ----------
        names : str or list
            Name of the variable(s).
        var : object or list
            The value(s) to pass.

        Examples
        --------
        >>> from oct2py import octave
        >>> y = [1, 2]
        >>> octave.put('y', y)
        >>> octave.get('y')
        array([1, 2])
        >>> octave.put(['x', 'y'], ['spam', [1, 2, 3, 4]])
        >>> octave.get(['x', 'y'])
        ('spam', array([1, 2, 3, 4]))

        """
        if isinstance(names, str):
            var = [var]
            names = [names]
        for name in names:
            if name.startswith('_'):
                raise Oct2PyError('Invalid name {0}'.format(name))
            if not self._writer.dummy_cell:
                self._get_dummy_cell()
        _, load_line = self._writer.create_file(var, names)
        self._eval(load_line, verbose=True)

    def get(self, var):
        """
        Retrieve a value from the Octave session.

        Parameters
        ----------
        var : str
            Name of the variable to retrieve.

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
          >>> octave.put('y', y)
          >>> octave.get('y')
          array([1, 2])
          >>> octave.put(['x', 'y'], ['spam', [1, 2, 3, 4]])
          >>> octave.get(['x', 'y'])
          ('spam', array([1, 2, 3, 4]))

        """
        if isinstance(var, str):
            var = [var]
        # make sure the variable(s) exist
        for variable in var:
            if self._eval("exist {0}".format(variable),
                          verbose=False) == 'ans = 0':
                raise Oct2PyError('{0} does not exist'.format(variable))
        argout_list, save_line = self._reader.setup(len(var), var)
        self._eval(save_line)
        return self._reader.extract_file(argout_list)

    def lookfor(self, string, verbose=False):
        """
        Call the Octave "lookfor" command.

        Uses with the "-all" switch to search within help strings.

        Parameters
        ----------
        string : str
            Search string for the lookfor command.
        verbose : bool, optional
            Print Octave output.

        Returns
        -------
        out : str
            Output from the Octave lookfor command.

        """
        return self.run('lookfor -all {0}'.format(string), verbose=verbose)

    def _eval(self, cmds, verbose=True, log=True):
        """
        Perform raw Octave command.

        This is a low-level command, and should not technically be used
        directly.  The API could change. You have been warned.

        Parameters
        ----------
        cmds : str or list
            Commands(s) to pass directly to Octave.
        verbose : bool, optional
            Print Octave output.

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
        resp = []
        # use ascii code 21 to signal an error and 3
        # to signal end of text
        if isinstance(cmds, str):
            cmds = [cmds]
        if verbose and log:
            [self.logger.info(line) for line in cmds]
        elif log:
            [self.logger.debug(line) for line in cmds]
        lines = ['try', '\n'.join(cmds), 'disp(char(3))',
                 'catch', 'disp(lasterr())', 'disp(char(21))',
                 'end', '']
        eval_ = '\n'.join(lines).encode('utf-8')
        try:
            self._session.stdin.write(eval_)
        except IOError:
            raise Oct2PyError('The session is closed')
        self._session.stdin.flush()
        syntax_error = False
        while 1:
            line = self._session.stdout.readline().rstrip().decode('utf-8')
            if line == '\x03':
                break
            elif line == '\x15':
                msg = ('Tried to run:\n"""\n{0}\n"""\nOctave returned:\n{1}'
                       .format('\n'.join(cmds), '\n'.join(resp)))
                raise Oct2PyError(msg)
            elif "syntax error" in line:
                syntax_error = True
            elif syntax_error and "^" in line:
                resp.append(line)
                msg = 'Octave Syntax Error\n'.join(resp)
                raise Oct2PyError(msg)
            elif verbose:
                self.logger.info(line)
            elif log:
                self.logger.debug(line)
            resp.append(line)
        return '\n'.join(resp)

    def _make_octave_command(self, name, doc=None):
        """Create a wrapper to an Octave procedure or object

        Adapted from the mlabwrap project

        """
        def octave_command(*args, **kwargs):
            """ Octave command """
            kwargs['nout'] = _get_nout()
            kwargs['verbose'] = False
            self._eval('clear {}'.format(name), log=False, verbose=False)
            return self.call(name, *args, **kwargs)
        # convert to ascii for pydoc
        doc = doc.encode('ascii', 'replace').decode('ascii')
        octave_command.__doc__ = "\n" + doc
        octave_command.__name__ = name
        return octave_command

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
        try:
            doc = self._eval('help {0}'.format(name), log=False, verbose=False)
        except Oct2PyError:
            try:
                doc = self._eval('type {0}'.format(name), log=False, verbose=False)
            except Oct2PyError:
                msg = '"{0}" is not a recognized octave command'.format(name)
                raise Oct2PyError(msg)
            else:
                # grab only the first line
                doc = doc.split('\n')[0]
        return doc

    def __getattr__(self, attr):
        """Magically creates a wapper to an Octave function or object.

        Adapted from the mlabwrap project.

        """
        if re.search(r'\W', attr):  # work around ipython <= 0.7.3 bug
            raise Oct2PyError(
                "Attributes don't look like this: {0}".format(attr))
        if attr.startswith('_'):
            raise Oct2PyError(
                "Octave commands do not start with _: {0}".format(attr))
        # print_ -> print
        if attr[-1] == "_":
            name = attr[:-1]
        else:
            name = attr
        doc = self._get_doc(name)
        octave_command = self._make_octave_command(name, doc)
        #!!! attr, *not* name, because we might have python keyword name!
        setattr(self, attr, octave_command)
        return octave_command

    def _set_graphics_toolkit(self):
        if self._graphics_toolkit == 'gnuplot':
            return
        try:
            self._eval("graphics_toolkit('gnuplot')", False)
        except Oct2PyError:
            pass
        self._graphics_toolkit = 'gnuplot'

    def _get_dummy_cell(self):
        '''Get a dummy cell variable for the matwriter
        '''
        self._writer.dummy_cell = object  # prevent recursion
        self.run('__cell = {[1]};')
        self.get('__cell')
        cell = self._reader.get_dummy_cell()
        self._writer.dummy_cell = cell

    def restart(self):
        '''Restart an Octave session in a clean state
        '''
        self._session = _open()
        self._isopen = True
        self._graphics_toolkit = None
        atexit.register(lambda handle=self._session: self.close(handle))
        self._reader = MatRead()
        self._writer = MatWrite()

    def __del__(self):
        """Close the Octave session before deletion.
        """
        self.close()


def _test():
    """Run the doctests for this module.
    """
    print('Starting doctest')
    doctest.testmod()
    print('Completed doctest')


if __name__ == "__main__":
    _test()
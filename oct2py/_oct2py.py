"""
.. module:: _oct2py
   :synopsis: Main module for oct2py package.
              Contains the Octave session object Oct2Py

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
import os
import re
import doctest
import atexit
from _h5write import H5Write
from _h5read import H5Read
from _utils import _open, _get_nout, _register_del, Oct2PyError


class Oct2Py(object):
    """Manages an Octave session.

    Uses HDF5 files to pass data between Octave and Numpy.
    The function must either exist as an m-file in this directory or
    on Octave's path.
    The first command will take about 0.5s for Octave to load up.
    The subsequent commands will be much faster.
    Plotting commands within an m file do not work unless you add this
    after every plot line: print -deps foo.eps

    """
    def __init__(self):
        """Start Octave and create our HDF helpers
        """
        self._session = _open()
        atexit.register(lambda handle=self._session: self._close(handle))
        self._reader = H5Read()
        self._writer = H5Write()

    def _close(self, handle=None):
        """Closes this octave session
        """
        if not handle:
            handle = self._session
        try:
            handle.stdin.write('exit\n')
        except (ValueError, TypeError, IOError):
            pass

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
        >>> print out
        y =
        <BLANKLINE>
            1        1        1
            1        1        1
            1        1        1
        <BLANKLINE>
        >>> octave.run('x = mean([[1, 2], [3, 4]])')
        'x =  2.5000'

        """
        # don't return a value from a script
        kwargs['nout'] = 0
        # this line is needed to force the plot to display
        for cmd in ['gplot', 'plot', 'bar', 'contour', 'hist', 'loglog',
                    'polar', 'semilogx', 'stairs', 'gsplot', 'mesh',
                    'meshdom']:
            if cmd in script:
                script += ';print -deps foo.eps;'
                _register_del('foo.eps')
                break
        return self.call(script, **kwargs)

    def call(self, func, *inputs, **kwargs):
        """
        Calls a function using Octave.

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
        >>> print b
        (1.0, 1.0, 0.0)
        >>> x, y = 1, 2
        >>> a = octave.call('zeros', x, y, verbose=True)
        a__ =
        <BLANKLINE>
                0        0
        <BLANKLINE>
        >>> U, S, V = octave.call('svd', [[1, 2], [1, 3]])
        >>> print U, S, V
        [[-0.57604844 -0.81741556]
        [-0.81741556  0.57604844]] [[ 3.86432845  0.        ]
        [ 0.          0.25877718]] [[-0.36059668 -0.93272184]
        [-0.93272184  0.36059668]]

        """
        verbose = kwargs.get('verbose', False)
        nout = kwargs.get('nout', _get_nout())

        # handle references to script names - and paths to them
        if func.endswith('.m'):
            if os.path.dirname(func):
                self.addpath(os.path.dirname(func))
                func = os.path.basename(func)
            func = func[:-2]

        # these three lines will form the commands sent to Octave
        # load("-hdf5", "infile", "invar1", ...)
        # [a, b, c] = foo(A, B, C)
        # save("-hdf5", "outfile", "outvar1", ...)
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
            call_line += ';print -deps foo.eps;'

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
        array([[1, 2]])
        >>> octave.put(['x', 'y'], ['spam', [1, 2, 3, 4]])
        >>> octave.get(['x', 'y'])
        ('spam', array([[1, 2, 3, 4]]))

        """
        if isinstance(names, str):
            var = [var]
            names = [names]
        for name in names:
            if name.startswith('_'):
                raise Oct2PyError('Invalid name {0}'.format(name))
        _, load_line = self._writer.create_file(var, names)
        self._eval(load_line, verbose=False)

    def get(self, var):
        """
        Retrieves a value from the Octave session

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
            If the variable does not exist in the Octave session

        Examples:
          >>> from oct2py import octave
          >>> y = [1, 2]
          >>> octave.put('y', y)
          >>> octave.get('y')
          array([[1, 2]])
          >>> octave.put(['x', 'y'], ['spam', [1, 2, 3, 4]])
          >>> octave.get(['x', 'y'])
          ('spam', array([[1, 2, 3, 4]]))

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
        Calls the Octave "lookfor" command

        Uses with the "-all" switch to search within help strings

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

    def _eval(self, cmds, verbose=True):
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
        resp = []
        # use ascii code 201 to signal an error and 200
        # to signal action complete
        if isinstance(cmds, str):
            cmds = [cmds]
        lines = ['try', '\n'.join(cmds), 'disp(char(200))',
                 'catch', 'disp(lasterr())', 'disp(char(201))',
                 'end', '']
        eval_ = '\n'.join(lines)
        self._session.stdin.write(eval_)
        while 1:
            line = self._session.stdout.readline().rstrip()
            if line == chr(200):
                break
            elif line == chr(201):
                msg = '"""\n{0}\n"""\n{0}'.format('\n'.join(cmds),
                                                  '\n'.join(resp))
                raise Oct2PyError(msg)
            elif verbose:
                print line
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
            return self.call(name, *args, **kwargs)
        octave_command.__doc__ = "\n" + doc
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
            doc = self._eval('help {0}'.format(name), verbose=False)
        except Oct2PyError:
            doc = self._eval('type {0}'.format(name), verbose=False)
            # grab only the first line
            doc = doc.split('\n')[0]
        return doc

    def __getattr__(self, attr):
        """Magically creates a wapper to an Octave function or object

        Adapted from the mlabwrap project

        """
        if re.search(r'\W', attr):  # work around ipython <= 0.7.3 bug
            raise ValueError(
                    "Attributes don't look like this: {0}".format(attr))
        if attr.startswith('_'):
            raise AttributeError(
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

    def __del__(self):
        """Closes the Octave session before deletion
        """
        self._close()


def _test():
    """Run the doctests for this module
    """
    doctest.testmod()


if __name__ == "__main__":
    _test()

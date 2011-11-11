''' py2oct - Python to GNU Octave bridge

Opens an Octave session to run commands and m-files.
Run py2oct_demo.py for a live demo of features.

Supports the running of any Octave function or m-file, and passing the
data seamlessly between Python and Octave using HDF files.

If you want to run legacy m-files, don't have Matlab(R), and don't fully trust
a code translator, this is your library.

All Octave variable types are mapped to comparable Python types.
Almost all Python types can be sent to Octave (including ndarrays),
   with the exception of cell arrays (lists with strings in them) of rank > 1.

There is a penalty for passing data via HDF files.  Running py2oct_speed.py
shows the effect.  After a startup time for the Octave engine (<1s),
raw function calls take almost no penalty.  The penalty for reading and
writing from the HDF file is around 5-10ms on my machine.  This
penalty is felt for both incoming and outgoing values.  As the data becomes
larger, the delay begins to increase (somewhere around a 100x100 array).
If you have any loops, you would be better served using a raw "run" command
for the loop rather than implementing the loop in python.

Plotting commands do not automatically result in the window being displayed
by Python.  In order to force the plot to be drawn, I have hacked the command
"print -deps foo.eps;'" onto anything that looks like a plot command, when
called using this package. If you have plot statements in your function that
you would like to display,you must add that line (replacing foo.eps
with the filename of your choice), after each plot statement.

Each instance of the Octave object has an independent session of Octave.
The library appears to be thread safe.  See py2oct_thread.py for an example of
several objects writing a different value for the same variable name
simultaneously and sucessfully retrieving their own result.

Future enhancements :
    - Add support for arbitrary outgoing cell arrays (rank > 1)
    - Add a Octave code compability check function
    - Add a feature to scan a file for plot statements and automatically
         add a line to print the plot, allowing Python to render it.

Note for Matlab(R) users: Octave supports most but not all of the core syntax
and commands.  See:
    http://www.gnu.org/software/octave/FAQ.html#MATLAB-compatibility

The main noticable differences are nested functions are not allowed,
  and GUIs (including uigetfile, etc.) are not supported.

There are several Octave packages (think toolboxes),
    including image and statistics:
    http://octave.sourceforge.net/packages.php

Similar work:
    pytave - Python to Octave bridge, but limited to POSIX systems (which is
                 why I made this one).
    mlabwrap - Python to Matlab bridge, requires a Matlab license.  I based
                my API on theirs.
    ompc, smop - Matlab to Python conversion tools.  Both rely on effective
                 parsing of code and a runtime helper library.  I would
                 love to see one or both of these projects render my project
                 unnecessary.  I borrowed the idea from ompc of using
                 introspection to find nargout dynamically.
'''
import os
import re
from h5write import OctaveH5Write
from h5read import OctaveH5Read
from helpers import _open, _close, _get_nout, OctaveError, OctaveStruct

# TODO: setup.py, test on linux, add to bitbucket, send link to Scipy


class Octave(object):
    """  Manages an Octave session

        Uses HDF5 files to pass data between Octave and Numpy - requires h5py

        Notes:
        The function must either exist as an m-file in this directory or
        on Octave's path.

        The first command will take about 0.5s for Octave to load up.
        The subsequent commands will be much faster.

        Plotting commands within an m file do not work
        Unless you add this after every plot line: print -deps foo.eps
    """
    def __init__(self):
        ''' Start Octave and create our HDF helpers
        '''
        self._session = _open()
        self._reader = OctaveH5Read()
        self._writer = OctaveH5Write()

    def run(self, script, **kwargs):
        ''' Runs artibrary octave code or an m-file

        Keywords implemented:
            verbose : If true, all m-file prints will be displayed

        Usage:
        run("y=ones(3,3)")
        run("x=zeros(3,3)", verbose=True)
        '''
        # don't return a value from a script
        kwargs['nout'] = 0
        # this line is needed to force the plot to display
        for cmd in ['gplot', 'plot', 'bar', 'contour', 'hist', 'loglog',
                    'polar', 'semilogx', 'stairs', 'gsplot', 'mesh',
                    'meshdom']:
            if cmd in script:
                script += ';print -deps foo.eps;'
                break
        return self.call(script, **kwargs)

    def call(self, func, *inputs, **kwargs):
        """  Calls a function using Octave

        Inputs:
            func (str) - Octave function or m-file to call
            inputs (list) - Variables to pass to the function
            kwargs (dict) - nout : number of arguments requested
                            verbose : whether to print the Octave output

                            *Note: nout is automatically set when calling this
                            function, using introspection (see usage below)

        Returns:
            If nout > 0, returns the values from Octave as a tuple
            Otherwise, returns the output displayed by Octave

        Usage:
          b = call('ones', 1, 2)
          x, y = 1, 2
          a = call('zeros', x, y, verbose=True)
          U, S, V = call('svd', ([[1,2], [1,3]]))
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
            call_line = '[%s] = ' % (', '.join(argout_list))
        if inputs:
            argin_list, load_line = self._writer.create_file(inputs)
            call_line += '%s(%s)' % (func, ', '.join(argin_list))
        elif nout:
            # call foo() - no arguments
            call_line += '%s()' % func
        else:
            # run foo
            call_line += '%s' % func
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

    def put(self, name, var):
        """ Puts a variable into the Octave session

        Inputs:
            name (str)- the name of the variable
            var  (object) - the variable itself

        Returns:
            The output printed by matlab

        Usage:
            y = [1, 2]
            put('y', y)
        """
        if isinstance(name, str):
            var = [var]
            name = [name]
        _, load_line = self._writer.create_file(var, name)
        return self._eval(load_line)

    def get(self, var):
        """ Retrieves a value from the Octave session

        Inputs:
            var (str or list) - the name of the variable to retrieve
                                 or a list of variable names
        Returns:
            If more than one variable, returns a tuple of variables.
            Otherwise, returns the variable.
            Raises an error if one of the variables does not exist.

        Usage:
            x= get('x')
            x, y = get(['x', 'y'])
        """
        if isinstance(var, str):
            var = [var]
        # make sure the variable(s) exist
        for variable in var:
            self._eval("type('%s')" % variable, verbose=False)
        argout_list, save_line = self._reader.setup(1, var)
        self._eval(save_line)
        return self._reader.extract_file(argout_list)

    def lookfor(self, string):
        ''' Calls the octave "lookfor" command, with the -all switch '''
        return self.run('lookfor -all %s' % string, verbose=True)

    def _eval(self, cmds, verbose=True):
        """ Performs the raw Octave command

        Inputs:
            cmds (str or list):  command(s) to pass directly to Octave
            verbose (bool) : If true, prints the Octave output

        Returns:
            The results printed by Octave
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
                msg = '"""\n%s\n"""\n%s' % ('\n'.join(cmds), '\n'.join(resp))
                raise OctaveError(msg)
            elif verbose:
                print line
            resp.append(line)
        return '\n'.join(resp)

    def _make_octave_command(self, name, doc=None):
        """ Called by __getattr__ to create a wrapper to a Octave,
        procedure or object on the fly

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
        """ Attempt to get the documentation of a name
        Return None if the name does not exist
        """
        try:
            doc = self._eval('help %s' % name, verbose=False)
        except OctaveError:
            doc = self._eval('type %s' % name, verbose=False)
            # grab only the first line
            doc = doc.split('\n')[0]
        return doc

    def __getattr__(self, attr):
        """ Magically creates a wapper to an octave function, procedure or
        object on-the-fly.
        Adapted from the mlabwrap project
        """
        if re.search(r'\W', attr):  # work around ipython <= 0.7.3 bug
            raise ValueError("Attributes don't look like this: %r" % attr)
        if attr.startswith('_'):
            raise AttributeError(
                            "Octave commands do not start with _: %s" % attr)
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
        """ Closes the Octave session before deletion """
        _close(self._session)


if __name__ == '__main__':
    oc = Octave()
    from py2oct_demo import demo
    from py2oct_speed import OctaveSpeed
    speed_test = OctaveSpeed()
    print "oc = Octave"
    print 'demo() runs the demo'
    print 'speed_test() runs the speed test'
    import code
    code.interact('', local=locals())

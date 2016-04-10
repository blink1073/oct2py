# -*- coding: utf-8 -*-
"""
===========
octavemagic
===========

Magics for interacting with Octave via oct2py.

.. note::

  The ``oct2py`` module needs to be installed separately and
  can be obtained using ``easy_install`` or ``pip``.

  You will also need a working copy of GNU Octave.

Usage
=====

To enable the magics below, execute ``%load_ext octavemagic``.

``%octave``

{OCTAVE_DOC}

``%octave_push``

{OCTAVE_PUSH_DOC}

``%octave_pull``

{OCTAVE_PULL_DOC}

"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2012 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import tempfile
from glob import glob
import os
from shutil import rmtree
import sys
import re

import oct2py
from xml.dom import minidom

from IPython.core.displaypub import publish_display_data
from IPython.core.magic import (Magics, magics_class, line_magic,
                                line_cell_magic, needs_local_scope)
from IPython.testing.skipdoctest import skip_doctest
from IPython.core.magic_arguments import (
    argument, magic_arguments, parse_argstring
)
from IPython.utils.py3compat import unicode_to_str
from IPython.utils.text import dedent


class OctaveMagicError(oct2py.Oct2PyError):
    pass

_mimetypes = {'png': 'image/png',
              'svg': 'image/svg+xml',
              'jpg': 'image/jpeg',
              'jpeg': 'image/jpeg'}


@magics_class
class OctaveMagics(Magics):

    """A set of magics useful for interactive work with Octave via oct2py.
    """

    def __init__(self, shell):
        """
        Parameters
        ----------
        shell : IPython shell

        """
        super(OctaveMagics, self).__init__(shell)
        self._oct = oct2py.octave
        if sys.platform == 'win32':
            # Use svg by default due to lack of Ghostscript on Windows Octave
            self._plot_format = 'svg'
        else:
            self._plot_format = 'png'

        # Allow publish_display_data to be overridden for
        # testing purposes.
        self._publish_display_data = publish_display_data

    def _fix_gnuplot_svg_size(self, image, size=None):
        """
        GnuPlot SVGs do not have height/width attributes.  Set
        these to be the same as the viewBox, so that the browser
        scales the image correctly.

        Parameters
        ----------
        image : str
            SVG data.
        size : tuple of int
            Image width, height.

        """
        (svg,) = minidom.parseString(image).getElementsByTagName('svg')
        viewbox = svg.getAttribute('viewBox').split(' ')

        if size is not None and size[0] is not None:
            width, height = size
        else:
            width, height = viewbox[2:]

        svg.setAttribute('width', '%dpx' % int(width))
        svg.setAttribute('height', '%dpx' % int(height))
        return svg.toxml()

    @skip_doctest
    @line_magic
    def octave_push(self, line):
        '''
        Line-level magic that pushes a variable to Octave.

        `line` should be made up of whitespace separated variable names in the
        IPython namespace::

            In [7]: import numpy as np

            In [8]: X = np.arange(5)

            In [9]: X.mean()
            Out[9]: 2.0

            In [10]: %octave_push X

            In [11]: %octave mean(X)
            Out[11]: 2.0

        '''
        inputs = line.split(' ')
        for input in inputs:
            input = unicode_to_str(input)
            self._oct.push(input, self.shell.user_ns[input])

    @skip_doctest
    @line_magic
    def octave_pull(self, line):
        '''
        Line-level magic that pulls a variable from Octave.

        ::

            In [18]: _ = %octave x = [1 2; 3 4]; y = 'hello'

            In [19]: %octave_pull x y

            In [20]: x
            Out[20]:
            array([[ 1.,  2.],
                   [ 3.,  4.]])

            In [21]: y
            Out[21]: 'hello'

        '''
        outputs = line.split(' ')
        for output in outputs:
            output = unicode_to_str(output)
            self.shell.push({output: self._oct.pull(output)})

    @skip_doctest
    @magic_arguments()
    @argument(
        '-i', '--input', action='append',
        help='Names of input variables to be pushed to Octave. Multiple names '
             'can be passed, separated by commas with no whitespace.'
    )
    @argument(
        '-o', '--output', action='append',
        help='Names of variables to be pulled from Octave after executing cell '
             'body. Multiple names can be passed, separated by commas with no '
             'whitespace.'
    )
    @argument(
        '-s', '--size', action='store',
        help='Pixel size of plots, "width,height". Default is "-s 400,250".'
    )
    @argument(
        '-f', '--format', action='store',
        help='Plot format (png, svg or jpg).'
    )
    @argument(
        '-g', '--gui', action='store_true', default=False,
        help='Show a gui for plots.  Default is False'
    )
    @needs_local_scope
    @argument(
        'code',
        nargs='*',
    )
    @line_cell_magic
    def octave(self, line, cell=None, local_ns=None):
        '''
        Execute code in Octave, and pull some of the results back into the
        Python namespace::

            In [9]: %octave X = [1 2; 3 4]; mean(X)
            Out[9]: array([[ 2., 3.]])

        As a cell, this will run a block of Octave code, without returning any
        value::

            In [10]: %%octave
               ....: p = [-2, -1, 0, 1, 2]
               ....: polyout(p, 'x')

            -2*x^4 - 1*x^3 + 0*x^2 + 1*x^1 + 2

        In the notebook, plots are published as the output of the cell, e.g.::

            %octave plot([1 2 3], [4 5 6])

        will create a line plot.

        Objects can be passed back and forth between Octave and IPython via the
        -i and -o flags in line::

            In [14]: Z = np.array([1, 4, 5, 10])

            In [15]: %octave -i Z mean(Z)
            Out[15]: array([ 5.])


            In [16]: %octave -o W W = Z * mean(Z)
            Out[16]: array([  5.,  20.,  25.,  50.])

            In [17]: W
            Out[17]: array([  5.,  20.,  25.,  50.])

        The size and format of output plots can be specified::

            In [18]: %%octave -s 600,800 -f svg
                ...: plot([1, 2, 3]);

        '''
        # match current working directory
        self._oct.cd(os.getcwd())

        args = parse_argstring(self.octave, line)

        # arguments 'code' in line are prepended to the cell lines
        if cell is None:
            code = ''
            return_output = True
        else:
            code = cell
            return_output = False

        code = ' '.join(args.code) + code

        # if there is no local namespace then default to an empty dict
        if local_ns is None:
            local_ns = {}

        if args.input:
            for input in ','.join(args.input).split(','):
                input = unicode_to_str(input)
                try:
                    val = local_ns[input]
                except KeyError:
                    val = self.shell.user_ns[input]
                self._oct.push(input, val)

        # generate plots in a temporary directory
        if args.gui:
            plot_dir = None
        else:
            plot_dir = tempfile.mkdtemp()

        if args.format is not None:
            plot_format = args.format
        elif sys.platform == 'win32' or sys.platform == 'darwin':
            # Use svg by default due to lack of Ghostscript on Windows Octave
            plot_format = 'svg'
        else:
            plot_format = 'png'

        plot_name = '__ipy_oct_fig_'

        if not args.size is None:
            plot_width, plot_height = [int(s) for s in args.size.split(',')]
        else:
            plot_width, plot_height = None, None

        try:
            text_output, value = self._oct.eval(code, plot_dir=plot_dir,
                                                plot_format=plot_format,
                                                plot_width=plot_width,
                                                plot_height=plot_height,
                                                plot_name=plot_name,
                                                verbose=False,
                                                return_both=True)
        except oct2py.Oct2PyError as exception:
            msg = str(exception)
            if 'Octave Syntax Error' in msg:
                raise OctaveMagicError(msg)
            msg = re.sub('"""\s+', '"""\n', msg)
            msg = re.sub('\s+"""', '\n"""', msg)
            raise OctaveMagicError(msg)

        

        key = 'OctaveMagic.Octave'
        display_data = []

        # Publish text output
        if text_output != "None":
            display_data.append((key, {'text/plain': text_output}))

        # Publish images
        images = []
        if not args.gui:
            for imgfile in glob("%s/*" % plot_dir):
                with open(imgfile, 'rb') as fid:
                    images.append(fid.read())
            try:
                rmtree(plot_dir, ignore_errors=True)
            except OSError:
                pass

        plot_mime_type = _mimetypes.get(plot_format, 'image/png')

        for image in images:
            if plot_format == 'svg':
                image = self._fix_gnuplot_svg_size(image, size=(plot_width,
                                                                plot_height))
            display_data.append((key, {plot_mime_type: image}))

        if args.output:
            for output in ','.join(args.output).split(','):
                output = unicode_to_str(output)
                self.shell.push({output: self._oct.pull(output)})

        for source, data in display_data:
            # source is deprecated in IPython 3.0.
            # specify with kwarg for backward compatibility.
            self._publish_display_data(source=source, data=data)

        if return_output:
            return value


__doc__ = __doc__.format(
    OCTAVE_DOC=dedent(OctaveMagics.octave.__doc__),
    OCTAVE_PUSH_DOC=dedent(OctaveMagics.octave_push.__doc__),
    OCTAVE_PULL_DOC=dedent(OctaveMagics.octave_pull.__doc__)
)


def load_ipython_extension(ip):
    """Load the extension in IPython."""
    ip.register_magics(OctaveMagics)

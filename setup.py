"""Setup script for oct2py package.

Run as::

    python setup.py install

"""
import sys
import os

from distutils.core import setup
from distutils.command.build import build
from oct2py import __version__


CLASSIFIERS = """\
Development Status :: 4 - Beta
Intended Audience :: Developers
Intended Audience :: Science/Research
License :: OSI Approved :: MIT License
Operating System :: OS Independent
Programming Language :: Python
Topic :: Scientific/Engineering
Topic :: Software Development
"""

try:
    from sphinx.setup_command import BuildDoc
    sphinx = True
except ImportError:
    msg = """No Sphinx module found. You have to install Sphinx to be able to
              generate the documentation."""
    print(' '.join(msg.split()))
    sphinx = False
    BuildDoc = object

# Sphinx build (documentation) - taken from the spyder project
# Copyright 2009-2011 Pierre Raybaut
# Licensed under the terms of the MIT License
class MyBuild(build):
   def has_doc(self):
        setup_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.isdir(os.path.join(setup_dir, 'doc'))
   sub_commands = build.sub_commands + [('build_sphinx', has_doc)]

class MyBuildDoc(BuildDoc):
    def run(self):
        build = self.get_finalized_command('build')
        sys.path.insert(0, os.path.abspath(build.build_lib))
        dirname = self.distribution.get_command_obj('build').build_purelib
        self.builder_target_dir = os.path.join(dirname, 'oct2py', 'doc')
        try:
            BuildDoc.run(self)
        except UnicodeDecodeError:
            print >>sys.stderr, "ERROR: unable to build documentation because Sphinx do not handle source path with non-ASCII characters. Please try to move the source package to another location (path with *only* ASCII characters)."
        sys.path.pop(0)

if sphinx:
   cmdclass = {'build': MyBuild, 'build_sphinx': MyBuildDoc}
   try:
       from sphinx_pypi_upload import UploadDoc
       cmdclass['upload_sphinx'] = UploadDoc
   except ImportError:
       pass
else:
   cmdclass = {}


setup(
    name='oct2py',
    version=__version__,
    author='Steven Silvester',
    author_email='steven.silvester@ieee.org',
    packages=['oct2py', 'oct2py.tests'],
    package_data={'oct2py': ['tests/*.m']},
    url='https://bitbucket.org/blink1073/oct2py/',
    license='MIT',
    platforms=["Any"],
    description='Python to GNU Octave bridge --> run m-files from python.',
    long_description=open('README.txt').read(),
    classifiers=filter(None, CLASSIFIERS.split('\n')),
    requires=["h5py (>=2.0.0)", "numpy (>=1.4.1)"],
    cmdclass=cmdclass,
    )

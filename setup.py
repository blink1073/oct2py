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

# Sphinx build (documentation)
class MyBuild(build):
   def has_doc(self):
        setup_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.isdir(os.path.join(setup_dir, 'doc'))
   sub_commands = build.sub_commands + [('build_sphinx', has_doc)]


try:
    from sphinx.setup_command import BuildDoc
    cmdclass = {'build': MyBuild, 'build_sphinx': BuildDoc}
except ImportError:
    msg = """No Sphinx module found. You have to install Sphinx to be able to
              generate the documentation."""
    print(' '.join(msg.split()))
    cmdclass = {}

setup(
    name='oct2py',
    version=__version__,
    author='Steven Silvester',
    author_email='steven.silvester@ieee.org',
    packages=['oct2py', 'oct2py.tests'],
    url='https://bitbucket.org/blink1073/oct2py/',
    license='LICENSE.txt',
    platforms=["Any"],
    package_data={'oct2py': ['tests/*.m']},
    description='Python to GNU Octave bridge --> run m-files from python.',
    long_description=open('README.txt').read(),
    classifiers=filter(None, CLASSIFIERS.split('\n')),
    requires=["h5py (>=2.0.0)"],
    cmdclass=cmdclass,
    )

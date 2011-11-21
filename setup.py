"""Setup script for oct2py package.

Run as::
    python setup.py install

"""
from distutils.core import setup
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
   cmdclss = {'build_sphinx': BuildDoc},
except ImportError:
   print 'Warning: Could not build sphinx documentation'
   cmdclss = {}

setup(
    name='oct2py',
    version=__version__,
    author='Steven Silvester',
    author_email='steven.silvester@ieee.org',
    packages=['oct2py', 'oct2py.tests'],
    url='https://bitbucket.org/blink1073/oct2py/',
    license='LICENSE.txt',
    platforms=["Any"],
    description='Python to GNU Octave bridge --> run m-files from python.',
    long_description=open('README.txt').read(),
    classifiers=filter(None, CLASSIFIERS.split('\n')),
    requires=["h5py (>=2.0.0)"],
    cmdclss=cmdclss,
    )

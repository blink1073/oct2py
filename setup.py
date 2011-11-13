'''
=====
Setup script for oct2py package.
=====

Run as::
    python setup.py install
'''
from distutils.core import setup

setup(
    name='oct2py',
    version='0.1.0',
    author='Steven M. Silvester',
    author_email='steven.silvester@ieee.org',
    packages=['oct2py', 'oct2py.test'],
    url='http://pypi.python.org/pypi/oct2py/',
    license='LICENSE.txt',
    description='Python to GNU Octave bridge --> run m-files from python',
    long_description=open('README.txt').read(),
    install_requires=[
        "h5py >= 2.0.1",
        "numpy == 1.6.0",
    ],
)

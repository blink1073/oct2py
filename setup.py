'''
=====
Setup script for oct2py package.
=====

Run as::
    python setup.py install
'''
from setuptools import setup

classifiers = """\
Development Status :: 4 - Beta
Intended Audience :: Developers
Intended Audience :: Science/Research
License :: OSI Approved :: MIT License
Operating System :: OS Independent
Programming Language :: Python
Topic :: Scientific/Engineering
Topic :: Software Development
"""

setup(
    name='oct2py',
    version='0.1.3',
    author='Steven M. Silvester',
    author_email='steven.silvester@ieee.org',
    packages=['oct2py', 'oct2py.tests'],
    url='https://bitbucket.org/blink1073/oct2py/',
    license='LICENSE.txt',
    platforms=["Any"],
    description='Python to GNU Octave bridge --> run m-files from python',
    long_description=open('README.txt').read(),
    classifiers=filter(None, classifiers.split('\n')),
    install_requires=[
        "h5py>=2.0.0"
    ],
)

"""Setup script for oct2py package.
"""
DISTNAME = 'oct2py'
DESCRIPTION = 'Python to GNU Octave bridge --> run m-files from python.'
LONG_DESCRIPTION = open('README.rst', 'rb').read().decode('utf-8')
MAINTAINER = 'Steven Silvester'
MAINTAINER_EMAIL = 'steven.silvester@ieee.org'
URL = 'http://github.com/blink1073/oct2py'
LICENSE = 'MIT'
REQUIRES = ["numpy (>= 1.7.1)", "scipy (>= 0.12)", "octave_kernel (>= 0.19)"]
INSTALL_REQUIRES = ["octave_kernel >= 0.19"]
PACKAGES = [DISTNAME, '%s.tests' % DISTNAME, '%s/ipython' % DISTNAME,
            '%s/ipython/tests' % DISTNAME]
PACKAGE_DATA = {DISTNAME: ['tests/*.m', '*.m']}
CLASSIFIERS = """\
Development Status :: 5 - Production/Stable
Intended Audience :: Developers
Intended Audience :: Science/Research
License :: OSI Approved :: MIT License
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3.3
Programming Language :: Python :: 3.4
Topic :: Scientific/Engineering
Topic :: Software Development
"""
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('oct2py/__init__.py', 'rb') as fid:
    for line in fid:
        line = line.decode('utf-8')
        if line.startswith('__version__'):
            version = line.strip().split()[-1][1:-1]
            break


setup(
    name=DISTNAME,
    version=version,
    maintainer=MAINTAINER,
    maintainer_email=MAINTAINER_EMAIL,
    packages=PACKAGES,
    package_data=PACKAGE_DATA,
    url=URL,
    download_url=URL,
    license=LICENSE,
    platforms=["Any"],
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    classifiers=list(filter(None, CLASSIFIERS.split('\n'))),
    requires=REQUIRES,
    install_requires=INSTALL_REQUIRES
 )

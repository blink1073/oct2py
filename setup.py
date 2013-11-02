"""Setup script for oct2py package.
"""
DISTNAME = 'oct2py'
DESCRIPTION = 'Python to GNU Octave bridge --> run m-files from python.'
LONG_DESCRIPTION = open('README.rst').read()
LONG_DESCRIPTION += '\n\n' + open('HISTORY.rst').read()
MAINTAINER = 'Steven Silvester'
MAINTAINER_EMAIL = 'steven.silvester@ieee.org'
URL = 'http://github.com/blink1073/oct2py'
LICENSE = 'MIT'
REQUIRES = ["numpy (>= 1.6.0)", "scipy (>= 0.9.0)"]
PACKAGES = [DISTNAME, '{0}.tests'.format(DISTNAME)]
PACKAGE_DATA = {DISTNAME: ['tests/*.m']}
CLASSIFIERS = """\
Development Status :: 5 - Production/Stable
Intended Audience :: Developers
Intended Audience :: Science/Research
License :: OSI Approved :: MIT License
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3.2
Programming Language :: Python :: 3.3
Topic :: Scientific/Engineering
Topic :: Software Development
"""
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
    

setup(
    name=DISTNAME,
    version=__import__(DISTNAME).__version__,
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
    classifiers=filter(None, CLASSIFIERS.split('\n')),
    requires=REQUIRES
 )

"""Setup script for oct2py package.
"""
import glob

DISTNAME = 'oct2py'
DESCRIPTION = 'Python to GNU Octave bridge --> run m-files from python.'
LONG_DESCRIPTION = open('README.rst', 'rb').read().decode('utf-8')
MAINTAINER = 'Steven Silvester'
MAINTAINER_EMAIL = 'steven.silvester@ieee.org'
URL = 'http://github.com/blink1073/oct2py'
LICENSE = 'MIT'
REQUIRES = ["numpy (>= 1.12)", "scipy (>= 0.17)", "octave_kernel (>= 0.31.0)"]
INSTALL_REQUIRES = ["octave_kernel >= 0.31.0", "numpy >= 1.12", "scipy >= 0.17"]
EXTRAS_REQUIRE = {
    'test': ['pytest', 'pandas', 'nbconvert'],
    'docs': ['sphinx', 'sphinx-bootstrap-theme', 'numpydoc']
}
PACKAGES = [DISTNAME, '%s.tests' % DISTNAME, '%s/ipython' % DISTNAME,
            '%s/ipython/tests' % DISTNAME]
PACKAGE_DATA = {DISTNAME: ['*.m'] + glob.glob('%s/**/*.m' % DISTNAME)}
CLASSIFIERS = """\
Development Status :: 5 - Production/Stable
Intended Audience :: Developers
Intended Audience :: Science/Research
License :: OSI Approved :: MIT License
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 3
Topic :: Scientific/Engineering
Topic :: Software Development
"""
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


import os
_version_py = os.path.join('.', 'oct2py', '_version.py')
version_ns = {}

with open(_version_py, mode='r') as version_file:
    exec(version_file.read(), version_ns)


setup(
    name=DISTNAME,
    version=version_ns['__version__'],
    maintainer=MAINTAINER,
    maintainer_email=MAINTAINER_EMAIL,
    packages=PACKAGES,
    package_data=PACKAGE_DATA,
    include_package_data=True,
    url=URL,
    download_url=URL,
    license=LICENSE,
    platforms=["Any"],
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/x-rst',
    classifiers=list(filter(None, CLASSIFIERS.split('\n'))),
    requires=REQUIRES,
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE
)

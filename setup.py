"""Setup script for oct2py package.
"""
DISTNAME = 'oct2py'
DESCRIPTION = 'Python to GNU Octave bridge --> run m-files from python.'
LONG_DESCRIPTION = open('README.rst').read()
MAINTAINER = 'Steven Silvester'
MAINTAINER_EMAIL = 'steven.silvester@ieee.org'
URL = 'http://github.com/blink1073/oct2py'
LICENSE = 'MIT'
VERSION = '1.0.0'
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
Topic :: Scientific/Engineering
Topic :: Software Development
"""
import sys
import os
from distutils.core import setup
from distutils.command.build import build
try:
    from distutils.command.build_py import build_py_2to3 as build_py
    print('Porting to Python 3...')
except ImportError:
    # 2.x
    from distutils.command.build_py import build_py

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
class MyBuild(build_py):
    def has_doc(self):
        setup_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.isdir(os.path.join(setup_dir, 'doc'))
    sub_commands = build.sub_commands + [('build_sphinx', has_doc)]


class MyBuildDoc(BuildDoc):
    def run(self):
        build = self.get_finalized_command('build')
        sys.path.insert(0, os.path.abspath(build.build_lib))
        self.builder_target_dir = 'build/doc/{0}/doc'.format(DISTNAME)
        BuildDoc.user_options
        try:
            BuildDoc.run(self)
        except UnicodeDecodeError:
            print >>sys.stderr, "ERROR: unable to build documentation because Sphinx do not handle source path with non-ASCII characters. Please try to move the source package to another location (path with *only* ASCII characters)."
        sys.path.pop(0)

if sphinx:
    cmdclass = {'build_py': MyBuild, 'build_sphinx': MyBuildDoc}
    try:
        from sphinx_pypi_upload import UploadDoc
        cmdclass['upload_sphinx'] = UploadDoc
    except ImportError:
        pass
else:
    cmdclass = {'build_py': build_py}


def write_version_py():
    fname = '{0}/version.py'.format(DISTNAME)
    fname = os.path.join(os.path.dirname(__file__), fname)
    with open(fname, 'w') as fid:
        fid.write('# THIS FILE IS GENERATED FROM THE {0} SETUP.PY\n'
                  .format(DISTNAME))
        fid.write("version = '{0}'\n".format(VERSION))
    os.chmod(fname, int('0666', 8))


if __name__ == '__main__':
    write_version_py()

    setup(
        name=DISTNAME,
        version=VERSION,
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
        requires=REQUIRES,
        cmdclass=cmdclass,
        command_options={
            'build_sphinx': {
                'project': ('setup.py', DISTNAME),
                'version': ('setup.py', '.'.join(VERSION.split('.')[:2])),
                'release': ('setup.py', VERSION),
                'all_files': ('setup.py', 1),
                'build_dir': ('setup.py', 'build/lib/{0}/doc'.format(DISTNAME))},
            'upload_sphinx': {
                'upload_dir': ('setup.py',
                               'build/doc/{0}/doc'.format(DISTNAME))}
            }
        )

"""Setup script for oct2py package.

Run as::

    python setup.py install

"""
DISTNAME            = 'oct2py'
DESCRIPTION         = 'Python to GNU Octave bridge --> run m-files from python.'
LONG_DESCRIPTION    = open('README.rst').read()
MAINTAINER          = 'Steven Silvester'
MAINTAINER_EMAIL    = 'steven.silvester@ieee.org'
URL                 = 'http://github.com/blink1073/oct2py'
LICENSE             = 'MIT'
VERSION             = '0.3.2'
CLASSIFIERS = """\
Development Status :: 4 - Beta
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
        dirname = self.distribution.get_command_obj('build').build_purelib
        self.builder_target_dir = os.path.join(dirname, 'oct2py', 'doc')
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

def write_version_py(filename='oct2py/version.py'):
    fname = os.path.join(os.path.dirname(__file__), filename)
    with open(fname, 'w') as fid:
        fid.write('# THIS FILE IS GENERATED FROM THE OCT2PY SETUP.PY\n')
        fid.write("version='{0}'\n".format(VERSION))

def write_setup_cfg():
    import ConfigParser
    config = ConfigParser.SafeConfigParser()
    config.add_section('build_sphinx')
    config.set('build_sphinx', 'source-dir', 'doc')
    config.set('build_sphinx', 'all_files', '1')
    version = '.'.join(VERSION.split('.')[:2])
    config.set('build_sphinx', 'version', version)
    config.set('build_sphinx', 'release', VERSION)
    config.add_section('upload_sphinx')
    config.set('upload_sphinx', 'upload-dir', 'build/lib/oc2py/doc')
    with open('setup.cfg', 'w') as fid:
        config.write(fid)

if __name__ == '__main__':
    write_version_py()
    write_setup_cfg()

    setup(
        name=DISTNAME,
        version=VERSION,
        maintainer=MAINTAINER,
        maintainer_email=MAINTAINER_EMAIL,
        packages=['oct2py', 'oct2py.tests'],
        package_data={'oct2py': ['tests/*.m']},
        url=URL,
        download_url=URL,
        license=LICENSE,
        platforms=["Any"],
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        classifiers=filter(None, CLASSIFIERS.split('\n')),
        requires=["numpy (>= 1.4.1)", "scipy (>= 0.9.0)"],
        cmdclass=cmdclass,
        )

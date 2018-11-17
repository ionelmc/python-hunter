#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import io
import os
import re
from distutils.command.build import build
from glob import glob
from itertools import chain
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import relpath
from os.path import splitext

from setuptools import Extension
from setuptools import find_packages
from setuptools import setup
from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from setuptools.command.easy_install import easy_install
from setuptools.command.install_lib import install_lib

try:
    # Allow installing package without any Cython available. This
    # assumes you are going to include the .c files in your sdist.
    import Cython
except ImportError:
    Cython = None


def read(*names, **kwargs):
    with io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ) as fh:
        return fh.read()


# Enable code coverage for C code: we can't use CFLAGS=-coverage in tox.ini, since that may mess with compiling
# dependencies (e.g. numpy). Therefore we set SETUPPY_CFLAGS=-coverage in tox.ini and copy it to CFLAGS here (after
# deps have been safely installed).
if 'TOXENV' in os.environ and 'SETUPPY_CFLAGS' in os.environ:
    os.environ['CFLAGS'] = os.environ['SETUPPY_CFLAGS']


class BuildWithPTH(build):
    def run(self):
        build.run(self)
        src = join(dirname(__file__), 'src', 'hunter.embed')
        path = join(dirname(__file__), 'src', 'hunter.pth')
        with open(src) as sh:
            with open(path, 'w') as fh:
                fh.write(
                    'import os, sys;'
                    'exec(%r)' % sh.read().replace('    ', ' ')
                )
        dest = join(self.build_lib, basename(path))
        self.copy_file(path, dest)


class EasyInstallWithPTH(easy_install):
    def run(self):
        easy_install.run(self)
        path = join(dirname(__file__), 'src', 'hunter.pth')
        dest = join(self.install_dir, basename(path))
        self.copy_file(path, dest)


class InstallLibWithPTH(install_lib):
    def run(self):
        install_lib.run(self)
        path = join(dirname(__file__), 'src', 'hunter.pth')
        dest = join(self.install_dir, basename(path))
        self.copy_file(path, dest)
        self.outputs = [dest]

    def get_outputs(self):
        return chain(install_lib.get_outputs(self), self.outputs)


class DevelopWithPTH(develop):
    def run(self):
        develop.run(self)
        path = join(dirname(__file__), 'src', 'hunter.pth')
        dest = join(self.install_dir, basename(path))
        self.copy_file(path, dest)


class OptionalBuildExt(build_ext):
    """Allow the building of C extensions to fail."""
    def run(self):
        try:
            if 'SETUPPY_NOEXT' in os.environ:
                raise Exception("C extensions disabled (SETUPPY_NOEXT)!")
            build_ext.run(self)
        except Exception as e:
            self._unavailable(e)
            self.extensions = []  # avoid copying missing files (it would fail).

    def _unavailable(self, e):
        print('*' * 80)
        print('''WARNING:

    An optional code optimization (C extension) could not be compiled.

    Optimizations for this package will not be available!
        ''')

        print('CAUSE:')
        print('')
        print('    ' + repr(e))
        print('*' * 80)


setup(
    name='hunter',
    version='2.1.0',
    license='BSD 2-Clause License',
    description='Hunter is a flexible code tracing toolkit.',
    long_description='%s\n%s' % (
        re.compile('^.. start-badges.*^.. end-badges', re.M | re.S).sub('', read('README.rst')),
        re.sub(':[a-z]+:`~?(.*?)`', r'``\1``', read('CHANGELOG.rst'))
    ),
    author='Ionel Cristian Mărieș',
    author_email='contact@ionelmc.ro',
    url='https://github.com/ionelmc/python-hunter',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Utilities',
        'Topic :: Software Development :: Debuggers',
    ],
    keywords=[
        'trace', 'tracer', 'settrace', 'debugger', 'debugging', 'code', 'source'
    ],
    install_requires=[
        'colorama',
        'six',
    ],
    extras_require={
        'remote': ['manhole>=1' '.' '5' '.' '0'],
    },
    entry_points={
        'console_scripts': [
            'hunter-trace = hunter.remote:main',
        ]
    },
    cmdclass={
        'build': BuildWithPTH,
        'easy_install': EasyInstallWithPTH,
        'install_lib': InstallLibWithPTH,
        'develop': DevelopWithPTH,
        'build_ext': OptionalBuildExt,
    },
    setup_requires=[
        'cython',
    ] if Cython else [],
    ext_modules=[
        Extension(
            splitext(relpath(path, 'src').replace(os.sep, '.'))[0],
            sources=[path],
            include_dirs=[dirname(path)]
        )
        for root, _, _ in os.walk('src')
        for path in glob(join(root, '*.pyx' if Cython else '*.c'))
    ],
)

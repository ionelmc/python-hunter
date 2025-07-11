#!/usr/bin/env python
import os
import re
import sys
from itertools import chain
from pathlib import Path

from setuptools import Extension
from setuptools import find_namespace_packages
from setuptools import setup
from setuptools.command.build import build
from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from setuptools.command.easy_install import easy_install
from setuptools.command.install_lib import install_lib
from setuptools.dist import Distribution

try:
    # Allow installing package without any Cython available. This
    # assumes you are going to include the .c files in your sdist.
    import Cython
except ImportError:
    Cython = None


# Enable code coverage for C code: we cannot use CFLAGS=-coverage in tox.ini, since that may mess with compiling
# dependencies (e.g. numpy). Therefore, we set SETUPPY_CFLAGS=-coverage in tox.ini and copy it to CFLAGS here (after
# deps have been safely installed).
if 'TOX_ENV_NAME' in os.environ and os.environ.get('SETUPPY_EXT_COVERAGE') == 'yes':
    CFLAGS = os.environ['CFLAGS'] = '-DCYTHON_TRACE=1 -DCYTHON_USE_SYS_MONITORING=0'
    LFLAGS = os.environ['LFLAGS'] = ''
else:
    CFLAGS = '-DCYTHON_USE_SYS_MONITORING=0'
    LFLAGS = ''

allow_extensions = True
if '__pypy__' in sys.builtin_module_names:
    print('NOTICE: C extensions disabled on PyPy (would be broken)!')
    allow_extensions = False
if os.environ.get('SETUPPY_FORCE_PURE'):
    print('NOTICE: C extensions disabled (SETUPPY_FORCE_PURE)!')
    allow_extensions = False

pth_file = str(Path(__file__).parent.joinpath('src', 'hunter.pth'))


class BuildWithPTH(build):
    def run(self):
        super().run()
        self.copy_file(pth_file, str(Path(self.build_lib, 'hunter.pth')))


class EasyInstallWithPTH(easy_install):
    def run(self, *args, **kwargs):
        super().run(*args, **kwargs)
        self.copy_file(pth_file, str(Path(self.install_dir, 'hunter.pth')))


class InstallLibWithPTH(install_lib):
    def run(self):
        super().run()
        dest = str(Path(self.install_dir, 'hunter.pth'))
        self.copy_file(pth_file, dest)
        self.outputs = [dest]

    def get_outputs(self):
        return chain(install_lib.get_outputs(self), self.outputs)


class DevelopWithPTH(develop):
    def run(self):
        super().run()
        self.copy_file(pth_file, str(Path(self.install_dir, 'hunter.pth')))


class OptionalBuildExt(build_ext):
    """
    Allow the building of C extensions to fail.
    """

    def run(self):
        try:
            super().run()
        except Exception as e:
            self._unavailable(e)
            self.extensions = []  # avoid copying missing files (it would fail).

    def _unavailable(self, e):
        print('*' * 80)
        print(
            """WARNING:

    An optional code optimization (C extension) could not be compiled.

    Optimizations for this package will not be available!
            """
        )

        print('CAUSE:')
        print('')
        print('    ' + repr(e))
        print('*' * 80)


class BinaryDistribution(Distribution):
    """
    Distribution which almost always forces a binary package with platform name
    """

    def has_ext_modules(self):
        return super().has_ext_modules() or not os.environ.get('SETUPPY_ALLOW_PURE')


def read(*names, **kwargs):
    with Path(__file__).parent.joinpath(*names).open(encoding=kwargs.get('encoding', 'utf8')) as fh:
        return fh.read()


setup(
    name='hunter',
    use_scm_version={
        'local_scheme': 'dirty-tag',
        'write_to': 'src/hunter/_version.py',
        'fallback_version': '3.8.0',
    },
    license='BSD-2-Clause',
    description='Hunter is a flexible code tracing toolkit.',
    long_description='{}\n{}'.format(
        re.compile('^.. start-badges.*^.. end-badges', re.M | re.S).sub('', read('README.rst')),
        re.sub(':[a-z]+:`~?(.*?)`', r'``\1``', read('CHANGELOG.rst')),
    ),
    long_description_content_type='text/x-rst',
    author='Ionel Cristian Mărieș',
    author_email='contact@ionelmc.ro',
    url='https://github.com/ionelmc/python-hunter',
    packages=find_namespace_packages('src'),
    package_dir={'': 'src'},
    py_modules=[path.stem for path in Path('src').glob('*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Utilities',
        'Topic :: Software Development :: Debuggers',
    ],
    project_urls={
        'Documentation': 'https://python-hunter.readthedocs.io/',
        'Changelog': 'https://python-hunter.readthedocs.io/en/latest/changelog.html',
        'Issue Tracker': 'https://github.com/ionelmc/python-hunter/issues',
    },
    keywords=[
        'trace',
        'tracer',
        'settrace',
        'debugger',
        'debugging',
        'code',
        'source',
    ],
    python_requires='>=3.9',
    install_requires=[],
    extras_require={
        ':platform_system != "Windows"': ['manhole >= 1.5'],
    },
    setup_requires=(
        [
            'setuptools_scm>=3.3.1,!=4.0.0',
            'cython',
        ]
        if Cython
        else [
            'setuptools_scm>=3.3.1,!=4.0.0',
        ]
    ),
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
    ext_modules=[
        Extension(
            str(path.relative_to('src').with_suffix('')).replace(os.sep, '.'),
            sources=[str(path)],
            extra_compile_args=CFLAGS.split(),
            extra_link_args=LFLAGS.split(),
            include_dirs=[str(path.parent)],
        )
        for path in Path('src').glob('**/*.pyx' if Cython else '**/*.c')
    ]
    if allow_extensions
    else [],
    distclass=BinaryDistribution if allow_extensions else None,
)

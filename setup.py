#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import, print_function

import io
import re
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

from distutils.command.build import build
from setuptools import find_packages
from setuptools import setup
from setuptools.command.easy_install import easy_install
from setuptools.command.develop import develop


def read(*names, **kwargs):
    return io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()


class BuildWithPTH(build):
    def run(self):
        build.run(self)
        for path in glob(join(dirname(__file__), 'src', '*.pth')):
            dest = join(self.build_lib, basename(path))
            self.copy_file(path, dest)


class EasyInstallWithPTH(easy_install):
    def run(self):
        easy_install.run(self)
        for path in glob(join(dirname(__file__), 'src', '*.pth')):
            dest = join(self.install_dir, basename(path))
            self.copy_file(path, dest)


class DevelopWithPTH(develop):
    def run(self):
        develop.run(self)
        for path in glob(join(dirname(__file__), 'src', '*.pth')):
            dest = join(self.install_dir, basename(path))
            self.copy_file(path, dest)


setup(
    name='hunter',
    version='0.2.0',
    license='BSD',
    description='Hunter is a flexible code tracing toolkit.',
    long_description='%s\n%s' % (read('README.rst'), re.sub(':[a-z]+:`~?(.*?)`', r'``\1``', read('CHANGELOG.rst'))),
    author='Ionel Cristian M\xc4\x83rie\xc8\x99',
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
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Utilities',
    ],
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    install_requires=[
        'fields',
        'colorama',
    ],
    extras_require={
        # eg: 'rst': ['docutils>=0.11'],
    },
    entry_points={
        'console_scripts': [
            'hunter = hunter.__main__:main'
        ]
    },
    cmdclass={
        'build': BuildWithPTH,
        'easy_install': EasyInstallWithPTH,
        'develop': DevelopWithPTH,
    },
)

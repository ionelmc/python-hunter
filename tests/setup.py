#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import os
from glob import glob
from os.path import dirname
from os.path import join
from os.path import relpath
from os.path import splitext

from setuptools import Extension
from setuptools import setup

try:
    # Allow installing package without any Cython available. This
    # assumes you are going to include the .c files in your sdist.
    import Cython
except ImportError:
    Cython = None

if __name__ == '__main__':
    setup(
        package_dir={'': 'tests'},
        zip_safe=False,
        setup_requires=[
            'cython',
        ] if Cython else [],
        ext_modules=[
            Extension(
                splitext(relpath(path, 'tests').replace(os.sep, '.'))[0],
                sources=[path],
                include_dirs=[dirname(path)],
                define_macros=[('CYTHON_TRACE', '1')]
            )
            for root, _, _ in os.walk('tests')
            for path in glob(join(root, '*.pyx' if Cython else '*.c'))
            ],
    )

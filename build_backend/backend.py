from setuptools import build_meta
from setuptools.build_meta import *  # noqa

if hasattr(build_meta, 'build_editable'):
    del build_editable  # noqa: F821

import os
import site
import stat
import sys
from distutils.sysconfig import get_python_lib

SITE_PACKAGES_PATHS = set()
if hasattr(site, 'getsitepackages'):
    SITE_PACKAGES_PATHS.update(site.getsitepackages())
if hasattr(site, 'getusersitepackages'):
    SITE_PACKAGES_PATHS.add(site.getusersitepackages())
SITE_PACKAGES_PATHS.add(get_python_lib())
SITE_PACKAGES_PATHS.add(os.path.dirname(os.path.dirname(__file__)))
SITE_PACKAGES_PATHS = tuple(SITE_PACKAGES_PATHS)

SYS_PREFIX_PATHS = {
    '<frozen zipimport>',
    '<frozen importlib._bootstrap>',
    '<frozen importlib._bootstrap_external>',
    sys.prefix,
    sys.exec_prefix,
    os.path.dirname(os.__file__),
    os.path.dirname(stat.__file__),
}
for prop in 'real_prefix', 'real_exec_prefix', 'base_prefix', 'base_exec_prefix':
    if hasattr(sys, prop):
        SYS_PREFIX_PATHS.add(getattr(sys, prop))

SYS_PREFIX_PATHS = tuple(sorted(SYS_PREFIX_PATHS, key=len, reverse=True))

import site
import sys
from distutils.sysconfig import get_python_lib

SITE_PACKAGES_PATHS = set()
if hasattr(site, 'getsitepackages'):
    SITE_PACKAGES_PATHS.update(site.getsitepackages())
if hasattr(site, 'getusersitepackages'):
    SITE_PACKAGES_PATHS.add(site.getusersitepackages())
SITE_PACKAGES_PATHS.add(get_python_lib())
SITE_PACKAGES_PATHS = tuple(SITE_PACKAGES_PATHS)

SYS_PREFIX_PATHS = set((
    sys.prefix,
    sys.exec_prefix
))
for prop in 'real_prefix', 'real_exec_prefix', 'base_prefix', 'base_exec_prefix':
    if hasattr(sys, prop):
        SYS_PREFIX_PATHS.add(getattr(sys, prop))
SYS_PREFIX_PATHS = tuple(SYS_PREFIX_PATHS)

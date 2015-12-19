import sys
from distutils.sysconfig import get_python_lib

SITE_PACKAGES_PATH = get_python_lib()
SYS_PREFIX_PATHS = (
    sys.prefix,
    sys.exec_prefix
)

for prop in 'real_prefix', 'real_exec_prefix', 'base_prefix', 'base_exec_prefix':
    if hasattr(sys, prop):
        SYS_PREFIX_PATHS += getattr(sys, prop),

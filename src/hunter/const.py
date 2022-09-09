import collections
import os
import site
import stat
import sys
import sysconfig

SITE_PACKAGES_PATHS = set()
for scheme in sysconfig.get_scheme_names():
    if scheme == 'posix_home':
        # it would appear this scheme is not for site-packages
        continue
    for name in ['platlib', 'purelib']:
        try:
            SITE_PACKAGES_PATHS.add(sysconfig.get_path(name, scheme))
        except KeyError:
            pass
if hasattr(site, 'getusersitepackages'):
    SITE_PACKAGES_PATHS.add(site.getusersitepackages())
if sys.version_info < (3, 10):
    from distutils.sysconfig import get_python_lib

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
    os.path.dirname(collections.__file__),
}
for prop in (
    'real_prefix',
    'real_exec_prefix',
    'base_prefix',
    'base_exec_prefix',
):
    if hasattr(sys, prop):
        SYS_PREFIX_PATHS.add(getattr(sys, prop))

SYS_PREFIX_PATHS = tuple(sorted(SYS_PREFIX_PATHS, key=len, reverse=True))

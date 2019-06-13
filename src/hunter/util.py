import re
import sys
import weakref
from itertools import chain

from colorama import Back
from colorama import Fore
from colorama import Style

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

try:
    from inspect import getattr_static
except ImportError:
    from .backports.inspect import getattr_static

try:
    from threading import main_thread
except ImportError:
    from threading import _shutdown
    get_main_thread = weakref.ref(
        _shutdown.__self__ if hasattr(_shutdown, '__self__') else _shutdown.im_self)
    del _shutdown
else:
    get_main_thread = weakref.ref(main_thread())

PY3 = sys.version_info[0] == 3

if PY3:
    STRING_TYPES = str,
else:
    STRING_TYPES = basestring,  # noqa

EVENT_COLORS = {
    'reset': Style.RESET_ALL,
    'normal': Style.NORMAL,
    'filename': '',
    'colon': Style.BRIGHT + Fore.BLACK,
    'lineno': Style.RESET_ALL,
    'kind': Fore.CYAN,
    'continuation': Style.BRIGHT + Fore.BLACK,
    'call': Style.BRIGHT + Fore.BLUE,
    'return': Style.BRIGHT + Fore.GREEN,
    'exception': Style.BRIGHT + Fore.RED,
    'detail': Style.NORMAL,
    'vars': Style.BRIGHT + Fore.MAGENTA,
    'vars-name': Style.NORMAL + Fore.MAGENTA,
    'internal-failure': Style.BRIGHT + Back.RED + Fore.RED,
    'internal-detail': Fore.WHITE,
    'source-failure': Style.BRIGHT + Back.YELLOW + Fore.YELLOW,
    'source-detail': Fore.WHITE,
}
CODE_COLORS = {
    'call': Fore.RESET + Style.BRIGHT,
    'line': Fore.RESET,
    'return': Fore.YELLOW,
    'exception': Fore.RED,
}
NO_COLORS = {key: '' for key in chain(CODE_COLORS, EVENT_COLORS)}
MISSING = type('MISSING', (), {'__repr__': lambda _: '?'})()
BUILTIN_SYMBOLS = set(vars(builtins))
CYTHON_SUFFIX_RE = re.compile(r'([.].+)?[.](so|pyd)$', re.IGNORECASE)
LEADING_WHITESPACE_RE = re.compile('(^[ \t]*)(?:[^ \t\n])', re.MULTILINE)


class cached_property(object):
    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


def get_func_in_mro(obj, code):
    """Attempt to find a function in a side-effect free way.

    This looks in obj's mro manually and does not invoke any descriptors.
    """
    val = getattr_static(obj, code.co_name, None)
    if val is None:
        return None
    if isinstance(val, (classmethod, staticmethod)):
        candidate = val.__func__
    elif isinstance(val, property) and (val.fset is None) and (val.fdel is None):
        candidate = val.fget
    else:
        candidate = val
    return if_same_code(candidate, code)


def if_same_code(func, code):
    while func is not None:
        func_code = getattr(func, '__code__', None)
        if func_code is code:
            return func
        # Attempt to find the decorated function
        func = getattr(func, '__wrapped__', None)
    return None

import sys
from itertools import chain

from colorama import Back
from colorama import Fore
from colorama import Style

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

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
    'continuation': Style.BRIGHT + Fore.BLUE,
    'call': Style.BRIGHT + Fore.BLUE,
    'return': Style.BRIGHT + Fore.GREEN,
    'exception': Style.BRIGHT + Fore.RED,
    'detail': Style.NORMAL,
    'vars': Style.RESET_ALL + Fore.MAGENTA,
    'vars-name': Style.BRIGHT,
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


class cached_property(object):
    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


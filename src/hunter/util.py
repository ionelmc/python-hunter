import ast
import io
import re
import sys
import types
import weakref
from collections import deque

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

OTHER_COLORS = {
    'COLON': Style.BRIGHT + Fore.BLACK,
    'LINENO': Style.RESET_ALL,
    'KIND': Fore.CYAN,
    'CONT': Style.BRIGHT + Fore.BLACK,
    'VARS': Style.BRIGHT + Fore.MAGENTA,
    'VARS-NAME': Style.NORMAL + Fore.MAGENTA,
    'INTERNAL-FAILURE': Style.BRIGHT + Back.RED + Fore.RED,
    'INTERNAL-DETAIL': Fore.WHITE,
    'SOURCE-FAILURE': Style.BRIGHT + Back.YELLOW + Fore.YELLOW,
    'SOURCE-DETAIL': Fore.WHITE,

    'RESET': Style.RESET_ALL,
}
for name, group in [
    ('', Style),
    ('fore', Fore),
    ('back', Back),
]:
    for key in dir(group):
        OTHER_COLORS['{}({})'.format(name, key) if name else key] = getattr(group, key)
CALL_COLORS = {
    'call': Style.BRIGHT + Fore.BLUE,
    'line': Fore.RESET,
    'return': Style.BRIGHT + Fore.GREEN,
    'exception': Style.BRIGHT + Fore.RED,
}
CODE_COLORS = {
    'call': Fore.RESET + Style.BRIGHT,
    'line': Fore.RESET,
    'return': Fore.YELLOW,
    'exception': Fore.RED,
}
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


def iter_symbols(code):
    """
    Iterate all the variable names in the given expression.

    Example:

    * ``self.foobar`` yields ``self``
    * ``self[foobar]`` yields `self`` and ``foobar``
    """
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.Name):
            yield node.id


def has_dict(obj_type, obj, tolerance=25):
    """
    A contrived mess to check that object doesn't have a __dit__ but avoid checking it if any ancestor is evil enough to
    explicitly define __dict__ (like apipkg.ApiModule has __dict__ as a property).
    """
    ancestor_types = deque()
    while obj_type is not type and tolerance:
        ancestor_types.appendleft(obj_type)
        obj_type = type(obj_type)
        tolerance -= 1
    for ancestor in ancestor_types:
        __dict__ = getattr(ancestor, '__dict__', None)
        if __dict__ is not None:
            if '__dict__' in __dict__:
                return True
    return hasattr(obj, '__dict__')


def safe_repr(obj, maxdepth=5):
    if not maxdepth:
        return '...'
    obj_type = type(obj)
    newdepth = maxdepth - 1

    # specifically handle few of the container builtins that would normally do repr on contained values
    if isinstance(obj, dict):
        if obj_type is not dict:
            return '%s({%s})' % (
                obj_type.__name__,
                ', '.join('%s: %s' % (
                    safe_repr(k, maxdepth),
                    safe_repr(v, newdepth)
                ) for k, v in obj.items()))
        else:
            return '{%s}' % ', '.join('%s: %s' % (
                safe_repr(k, maxdepth),
                safe_repr(v, newdepth)
            ) for k, v in obj.items())
    elif isinstance(obj, list):
        if obj_type is not list:
            return '%s([%s])' % (obj_type.__name__, ', '.join(safe_repr(i, newdepth) for i in obj))
        else:
            return '[%s]' % ', '.join(safe_repr(i, newdepth) for i in obj)
    elif isinstance(obj, tuple):
        if obj_type is not tuple:
            return '%s(%s%s)' % (
                obj_type.__name__,
                ', '.join(safe_repr(i, newdepth) for i in obj),
                ',' if len(obj) == 1 else '')
        else:
            return '(%s%s)' % (', '.join(safe_repr(i, newdepth) for i in obj), ',' if len(obj) == 1 else '')
    elif isinstance(obj, set):
        if obj_type is not set:
            return '%s({%s})' % (obj_type.__name__, ', '.join(safe_repr(i, newdepth) for i in obj))
        else:
            return '{%s}' % ', '.join(safe_repr(i, newdepth) for i in obj)
    elif isinstance(obj, frozenset):
        return '%s({%s})' % (obj_type.__name__, ', '.join(safe_repr(i, newdepth) for i in obj))
    elif isinstance(obj, deque):
        return '%s([%s])' % (obj_type.__name__, ', '.join(safe_repr(i, newdepth) for i in obj))
    elif isinstance(obj, BaseException):
        return '%s(%s)' % (obj_type.__name__, ', '.join(safe_repr(i, newdepth) for i in obj.args))
    elif obj_type in (type, types.ModuleType,
                      types.FunctionType, types.MethodType,
                      types.BuiltinFunctionType, types.BuiltinMethodType,
                      io.IOBase):
        # hardcoded list of safe things. note that isinstance ain't used
        # (we don't trust subclasses to do the right thing in __repr__)
        return repr(obj)
    elif not has_dict(obj_type, obj):
        return repr(obj)
    else:
        # if the object has a __dict__ then it's probably an instance of a pure python class, assume bad things
        #  with side-effects will be going on in __repr__ - use the default instead (object.__repr__)
        return object.__repr__(obj)

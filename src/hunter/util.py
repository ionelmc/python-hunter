import ast
import re
import sys
import types
import weakref
from collections import Counter
from collections import OrderedDict
from collections import defaultdict
from collections import deque
from datetime import date
from datetime import datetime
from inspect import CO_VARARGS
from inspect import CO_VARKEYWORDS

from .vendor.colorama import Back
from .vendor.colorama import Fore
from .vendor.colorama import Style

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

try:
    from types import InstanceType
except ImportError:
    InstanceType = object()

try:
    from re import Pattern
except ImportError:
    Pattern = type(re.compile(''))


try:
    from re import RegexFlag
except ImportError:
    RegexFlag = int

PY3 = sys.version_info[0] == 3

if PY3:
    StringType = str,
else:
    StringType = basestring,  # noqa

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

if PY3:
    def get_arguments(code):
        co_varnames = code.co_varnames
        co_argcount = code.co_argcount
        co_kwonlyargcount = code.co_kwonlyargcount
        kwonlyargs = co_varnames[co_argcount:co_argcount + co_kwonlyargcount]
        for arg in co_varnames[:co_argcount]:
            yield '', arg
        co_argcount += co_kwonlyargcount
        if code.co_flags & CO_VARARGS:
            yield '*', co_varnames[co_argcount]
            co_argcount = co_argcount + 1
        for arg in kwonlyargs:
            yield '', arg
        if code.co_flags & CO_VARKEYWORDS:
            yield '**', co_varnames[co_argcount]
else:
    from inspect import getargs

    def get_arguments(code):
        arguments = getargs(code)
        for arg in flatten(arguments.args):
            yield '', arg
        if arguments.varargs:
            yield '*', arguments.varargs
        if arguments.keywords:
            yield '**', arguments.keywords


def flatten(something):
    if isinstance(something, (list, tuple)):
        for element in something:
            for subelement in flatten(element):
                yield subelement
    else:
        yield something


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


def safe_repr(obj, maxdepth=5):
    if not maxdepth:
        return '...'
    obj_type = type(obj)
    obj_type_type = type(obj_type)
    newdepth = maxdepth - 1

    # only represent exact builtins
    # (subclasses can have side-effects due to __class__ as a property, __instancecheck__, __subclasscheck__ etc)
    if obj_type is dict:
        return '{%s}' % ', '.join('%s: %s' % (
            safe_repr(k, maxdepth),
            safe_repr(v, newdepth)
        ) for k, v in obj.items())
    elif obj_type is list:
        return '[%s]' % ', '.join(safe_repr(i, newdepth) for i in obj)
    elif obj_type is tuple:
        return '(%s%s)' % (', '.join(safe_repr(i, newdepth) for i in obj), ',' if len(obj) == 1 else '')
    elif obj_type is set:
        return '{%s}' % ', '.join(safe_repr(i, newdepth) for i in obj)
    elif obj_type is frozenset:
        return '%s({%s})' % (obj_type.__name__, ', '.join(safe_repr(i, newdepth) for i in obj))
    elif obj_type is deque:
        return '%s([%s])' % (obj_type.__name__, ', '.join(safe_repr(i, newdepth) for i in obj))
    elif obj_type in (Counter, OrderedDict, defaultdict):
        return '%s({%s})' % (
            obj_type.__name__,
            ', '.join('%s: %s' % (
                safe_repr(k, maxdepth),
                safe_repr(v, newdepth)
            ) for k, v in obj.items())
        )
    elif obj_type is Pattern:
        if obj.flags:
            return 're.compile(%s, flags=%s)' % (
                safe_repr(obj.pattern),
                RegexFlag(obj.flags),
            )
        else:
            return 're.compile(%s)' % safe_repr(obj.pattern)
    elif obj_type is date:
        return repr(obj)
    elif obj_type is datetime:
        return '%s(%d, %d, %d, %d, %d, %d, %d, tzinfo=%s)' % (
            obj_type.__name__,
            obj.year, obj.month, obj.day,
            obj.hour, obj.minute, obj.second, obj.microsecond,
            safe_repr(obj.tzinfo)
        )
    elif obj_type is types.MethodType:  # noqa
        self = obj.__self__
        name = getattr(obj, '__qualname__', None)
        if name is None:
            name = obj.__name__
        return '<%sbound method %s of %s>' % ('un' if self is None else '', name, safe_repr(self, newdepth))
    elif obj_type_type is type and BaseException in obj_type.__mro__:
        return '%s(%s)' % (obj_type.__name__, ', '.join(safe_repr(i, newdepth) for i in obj.args))
    elif obj_type_type is type and obj_type is not InstanceType and obj_type.__module__ in (builtins.__name__, 'io', 'socket', '_socket'):
        # hardcoded list of safe things. note that isinstance ain't used
        # (we don't trust subclasses to do the right thing in __repr__)
        return repr(obj)
    else:
        # if the object has a __dict__ then it's probably an instance of a pure python class, assume bad things
        #  with side-effects will be going on in __repr__ - use the default instead (object.__repr__)
        return object.__repr__(obj)


def frame_iterator(frame):
    """
    Yields frames till there are no more.
    """
    while frame:
        yield frame
        frame = frame.f_back

import io
import sys
import types
from collections import deque

PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
else:
    string_types = basestring,  # noqa


class cached_property(object):
    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


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
    elif not hasdict(obj_type, obj):
        return repr(obj)
    else:
        # if the object has a __dict__ then it's probably an instance of a pure python class, assume bad things
        #  with side-effects will be going on in __repr__ - use the default instead (object.__repr__)
        return object.__repr__(obj)


def hasdict(obj_type, obj, tolerance=25):
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

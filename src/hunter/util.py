import io
import types
from collections import deque


class cached_property(object):
    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


def rudimentary_repr(obj, maxdepth=5):
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
                    rudimentary_repr(k, maxdepth),
                    rudimentary_repr(v, newdepth)
                ) for k, v in obj.items()))
        else:
            return '{%s}' % ', '.join('%s: %s' % (
                rudimentary_repr(k, maxdepth),
                rudimentary_repr(v, newdepth)
            ) for k, v in obj.items())
    elif isinstance(obj, list):
        if obj_type is not list:
            return '%s([%s])' % (obj_type.__name__, ', '.join(rudimentary_repr(i, newdepth) for i in obj))
        else:
            return '[%s]' % ', '.join(rudimentary_repr(i, newdepth) for i in obj)
    elif isinstance(obj, tuple):
        if obj_type is not tuple:
            return '%s(%s%s)' % (
                obj_type.__name__,
                ', '.join(rudimentary_repr(i, newdepth) for i in obj),
                ',' if len(obj) == 1 else '')
        else:
            return '(%s%s)' % (', '.join(rudimentary_repr(i, newdepth) for i in obj), ',' if len(obj) == 1 else '')
    elif isinstance(obj, set):
        if obj_type is not set:
            return '%s({%s})' % (obj_type.__name__, ', '.join(rudimentary_repr(i, newdepth) for i in obj))
        else:
            return '{%s}' % ', '.join(rudimentary_repr(i, newdepth) for i in obj)
    elif isinstance(obj, frozenset):
        return '%s({%s})' % (obj_type.__name__, ', '.join(rudimentary_repr(i, newdepth) for i in obj))
    elif isinstance(obj, deque):
        return '%s([%s])' % (obj_type.__name__, ', '.join(rudimentary_repr(i, newdepth) for i in obj))
    elif isinstance(obj, BaseException):
        return '%s(%s)' % (obj_type.__name__, ', '.join(rudimentary_repr(i, newdepth) for i in obj.args))
    elif obj_type in (type, types.ModuleType,
                      types.FunctionType, types.MethodType,
                      types.BuiltinFunctionType, types.BuiltinMethodType,
                      io.IOBase):
        # hardcoded list of safe things. note that isinstance ain't used
        # (we don't trust subclasses to do the right thing in __repr__)
        return repr(obj)
    elif not hasattr(obj, '__dict__'):
        # note that this could be `not hasattr(obj, '__dict__') and not hasattr(obj, '__slots__')`
        # but lots of objects safe to repr (like sockets) have __slots__
        # (I don't want to have the burden of maintaining a huge list of safe to repr types)
        #
        # the assumption is that if you use __slots__ you know what you're doing and you ain't gonna be stupid enough to
        # have a side-effect in __repr__ (I hope ...)
        return repr(obj)
    else:
        # if the object has a __dict__ then it's probably an instance of a pure python class, assume bad things
        #  with side-effects will be going on in __repr__ - use the default instead (object.__repr__)
        return object.__repr__(obj)

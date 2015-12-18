from __future__ import absolute_import

import atexit
import inspect
import linecache
import os
import re
import sys
import tokenize
from functools import partial
from itertools import chain

from fields import Fields
from six import string_types

from .actions import CodePrinter
from .env import SITE_PACKAGES_PATH
from .env import SYS_PREFIX_PATHS

STARTSWITH_TYPES = (list, tuple, set)


class Tracer(object):
    """
    Trace object.

    """

    def __init__(self):
        self._handler = None
        self._previous_tracer = None

    def __str__(self):
        return "Tracer(_handler={}, _previous_tracer={})".format(
            "<not started>" if self._handler is None else self._handler,
            self._previous_tracer,
        )

    def __call__(self, frame, kind, arg):
        """
        The settrace function.

        .. note::

            This always returns self (drills down) - as opposed to only drilling down when predicate(event) is True because it might
            match further inside.
        """
        if self._handler is None:
            raise RuntimeError("Tracer is not started.")

        self._handler(Event(frame, kind, arg, self))

        if self._previous_tracer:
            self._previous_tracer(frame, kind, arg)
        return self

    def trace(self, *predicates, **options):
        """
        Starts tracing. Can be used as a context manager (with slightly incorrect semantics - it starts tracing before ``__enter__`` is
        called).

        Args:
            predicates (:class:`hunter.Q` instances): Runs actions if any of the given predicates match.
            options: Keyword arguments that are passed to :class:`hunter.Q`, for convenience.
        """
        if "action" not in options and "actions" not in options:
            options["action"] = CodePrinter
        merge = options.pop("merge", True)
        clear_env_var = options.pop("clear_env_var", False)
        predicate = Q(*predicates, **options)

        if clear_env_var:
            os.environ.pop("PYTHONHUNTER", None)

        previous_tracer = sys.gettrace()
        if previous_tracer is self:
            if merge:
                self._handler |= predicate
        else:
            sys.settrace(self)

            self._previous_tracer = previous_tracer
            self._handler = predicate
        return self

    def stop(self):
        """
        Stop tracing. Restores previous tracer (if any).
        """
        sys.settrace(self._previous_tracer)
        self._previous_tracer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

_tracer = Tracer()
trace = _tracer.trace
stop = atexit.register(_tracer.stop)


class _CachedProperty(object):
    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class Event(Fields.kind.function.module.filename):
    """
    Event wrapper for ``frame, kind, arg`` (the arguments the settrace function gets).

    Provides few convenience properties.
    """
    frame = None
    kind = None
    arg = None
    tracer = None

    def __init__(self, frame, kind, arg, tracer):
        self.frame = frame
        self.kind = kind
        self.arg = arg
        self.tracer = tracer

    @_CachedProperty
    def locals(self):
        """
        A dict with local variables.
        """
        return self.frame.f_locals

    @_CachedProperty
    def globals(self):
        """
        A dict with global variables.
        """
        return self.frame.f_globals

    @_CachedProperty
    def function(self):
        """
        A string with function name.
        """
        return self.code.co_name

    @_CachedProperty
    def module(self):
        """
        A string with module name (eg: ``"foo.bar"``).
        """
        module = self.frame.f_globals.get('__name__', '')
        if module is None:
            module = ''

        return module

    @_CachedProperty
    def filename(self):
        """
        A string with absolute path to file.
        """
        filename = self.frame.f_globals.get('__file__', '')
        if filename is None:
            filename = ''

        if filename.endswith(('.pyc', '.pyo')):
            filename = filename[:-1]
        elif filename.endswith('$py.class'):  # Jython
            filename = filename[:-9] + ".py"

        return filename

    @_CachedProperty
    def lineno(self):
        """
        An integer with line number in file.
        """
        return self.frame.f_lineno

    @_CachedProperty
    def code(self):
        """
        A code object (not a string).
        """
        return self.frame.f_code

    @_CachedProperty
    def stdlib(self):
        """
        A boolean flag. ``True`` if frame is in stdlib.
        """
        if self.filename.startswith(SITE_PACKAGES_PATH):
            # if it's in site-packages then its definitely not stdlib
            return False
        if self.filename.startswith(SYS_PREFIX_PATHS):
            return True

    @_CachedProperty
    def fullsource(self, getlines=linecache.getlines):
        """
        A string with the sourcecode for the current statement (from ``linecache`` - failures are ignored).

        May include multiple lines if it's a class/function definition (will include decorators).
        """
        try:
            return self._raw_fullsource
        except Exception as exc:
            return "??? NO SOURCE: {!r}".format(exc)

    @_CachedProperty
    def source(self, getline=linecache.getline):
        """
        A string with the sourcecode for the current line (from ``linecache`` - failures are ignored).

        Fast but sometimes incomplete.
        """
        try:
            return getline(self.filename, self.lineno)
        except Exception as exc:
            return "??? NO SOURCE: {!r}".format(exc)

    @_CachedProperty
    def _raw_fullsource(self, getlines=linecache.getlines, getline=linecache.getline):
        if self.kind == 'call' and self.code.co_name != "<module>":
            lines = []
            try:
                for _, token, _, _, line in tokenize.generate_tokens(partial(
                    next,
                    yield_lines(self.filename, self.lineno - 1, lines.append)
                )):
                    if token in ("def", "class", "lambda"):
                        return ''.join(lines)
            except tokenize.TokenError:
                pass

        return getline(self.filename, self.lineno)

    __getitem__ = object.__getattribute__


def yield_lines(filename, start, collector,
                limit=10,
                getlines=linecache.getlines,
                leading_whitespace_re=re.compile('(^[ \t]*)(?:[^ \t\n])', re.MULTILINE)):
    dedent = None
    amount = 0
    for line in getlines(filename)[start:start + limit]:
        if dedent is None:
            dedent = leading_whitespace_re.findall(line)
            dedent = dedent[0] if dedent else ""
            amount = len(dedent)
        elif not line.startswith(dedent):
            break
        collector(line)
        yield line[amount:]


def Q(*predicates, **query):
    """
    Handles situations where :class:`hunter.Query` objects (or other callables) are passed in as positional arguments.
    Conveniently converts that to an :class:`hunter.Or` predicate.
    """
    optional_actions = query.pop("actions", [])
    if "action" in query:
        optional_actions.append(query.pop("action"))

    if predicates:
        predicates = tuple(
            p() if inspect.isclass(p) and issubclass(p, Action) else p
            for p in predicates
        )
        if any(isinstance(p, CodePrinter) for p in predicates):
            if CodePrinter in optional_actions:
                optional_actions.remove(CodePrinter)
        if query:
            predicates += Query(**query),

        result = Or(*predicates)
    else:
        result = Query(**query)

    if optional_actions:
        result = When(result, *optional_actions)

    return result


class Query(Fields.query):
    """
    A query class.

    See :class:`hunter.Event` for fields that can be filtered on.
    """
    query = ()
    allowed = tuple(i for i in Event.__dict__.keys() if not i.startswith('_'))

    def __init__(self, **query):
        """
        Args:
            query: criteria to match on.

                Accepted arguments: ``arg``, ``code``, ``filename``, ``frame``, ``fullsource``, ``function``,
                ``globals``, ``kind``, ``lineno``, ``locals``, ``module``, ``source``, ``stdlib``, ``tracer``.
        """
        for key in query:
            if key not in self.allowed:
                raise TypeError("Unexpected argument {!r}. Must be one of {}.".format(key, self.allowed))
        self.query = query

    def __repr__(self):
        return "Query({})".format(
            ', '.join("{}={!r}".format(*item) for item in self.query.items()),
        )

    def __call__(self, event):
        """
        Handles event. Returns True if all criteria matched.
        """
        for key, value in self.query.items():
            evalue = event[key]
            if isinstance(evalue, string_types) and isinstance(value, STARTSWITH_TYPES):
                if not evalue.startswith(tuple(value)):
                    return False
            elif evalue != value:
                return False

        return True

    def __or__(self, other):
        """
        Convenience API so you can do ``Q() | Q()``. It converts that to ``Or(Q(), Q())``.
        """
        return Or(self, other)

    def __and__(self, other):
        """
        Convenience API so you can do ``Q() & Q()``. It converts that to ``And(Q(), Q())``.
        """
        return And(self, other)


class When(Fields.condition.actions):
    """
    Runs ``actions`` when ``condition(event)`` is ``True``.

    Actions take a single ``event`` argument.
    """
    def __init__(self, condition, *actions):
        if not actions:
            raise TypeError("Must give at least one action.")
        super(When, self).__init__(condition, [
            action() if inspect.isclass(action) and issubclass(action, Action) else action
            for action in actions
        ])

    def __call__(self, event):
        """
        Handles the event.
        """
        if self.condition(event):
            for action in self.actions:
                action(event)

            return True

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)


def _with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(meta):

        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)
    return type.__new__(metaclass, 'temporary_class', (), {})


class _UnwrapSingleArgumentMetaclass(type):
    def __call__(cls, predicate, *predicates):
        if not predicates:
            return predicate
        else:
            all_predicates = []

            for p in chain((predicate,), predicates):
                if isinstance(p, cls):
                    all_predicates.extend(p.predicates)
                else:
                    all_predicates.append(p)
            return super(_UnwrapSingleArgumentMetaclass, cls).__call__(*all_predicates)


class And(_with_metaclass(_UnwrapSingleArgumentMetaclass, ~Fields.predicates)):
    """
    `And` predicate. Exits at the first sub-predicate that returns ``False``.
    """
    def __init__(self, *predicates):
        self.predicates = predicates

    def __str__(self):
        return "And({})".format(', '.join(str(p) for p in self.predicates))

    def __call__(self, event):
        """
        Handles the event.
        """
        for predicate in self.predicates:
            if not predicate(event):
                return False
        return True

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(*chain(self.predicates, other.predicates if isinstance(other, And) else (other,)))


class Or(_with_metaclass(_UnwrapSingleArgumentMetaclass, ~Fields.predicates)):
    """
    `Or` predicate. Exits at first sub-predicate that returns ``True``.
    """
    def __init__(self, *predicates):
        self.predicates = predicates

    def __call__(self, event):
        """
        Handles the event.
        """
        for predicate in self.predicates:
            if predicate(event):
                return True
        return False

    def __or__(self, other):
        return Or(*chain(self.predicates, other.predicates if isinstance(other, Or) else (other,)))

    def __and__(self, other):
        return And(self, other)


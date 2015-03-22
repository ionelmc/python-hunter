from __future__ import absolute_import
from __future__ import unicode_literals

import inspect
import linecache
import os
import pdb
import sys
from itertools import chain

from fields import Fields


__version__ = "0.1.0"
__all__ = 'F', 'When', 'And', 'Or', 'CodePrinter', 'Debugger', 'VarsPrinter', 'trace', 'stop'

DEFAULT_MIN_FILENAME_ALIGNMENT = 15


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

        self._handler(Event(frame, kind, arg))

        if self._previous_tracer:
            self._previous_tracer(frame, kind, arg)
        return self

    def trace(self, *predicates, **options):
        """
        Starts tracing. Can be used as a context manager (with slightly incorrect semantics - it starts tracing before ``__enter__`` is
        called).

        Args:
            predicates (:class:`hunter.F` instances): Runs actions if any of the given predicates match.
            options: Keyword arguments that are passed to :class:`hunter.F`, for convenience.
        """
        if "action" not in options and "actions" not in options:
            options["action"] = CodePrinter()
        predicate = F(*predicates, **options)

        previous_tracer = sys.gettrace()
        if previous_tracer is self:
            self._handler |= predicate
        else:
            self._previous_tracer = previous_tracer
            self._handler = predicate
            sys.settrace(self)
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
stop = _tracer.stop


class CachedProperty(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls):
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class Event(object):
    """
    Event wrapper for ``frame, kind, arg`` (the arguments the settrace function gets).

    Provides few convenience properties.
    """

    def __init__(self, frame, kind, arg):
        self.frame = frame
        self.kind = kind
        self.arg = arg

    @CachedProperty
    def locals(self):
        return self.frame.f_locals

    @CachedProperty
    def globals(self):
        return self.frame.f_locals

    @CachedProperty
    def function(self):
        return self.frame.f_code.co_name

    @CachedProperty
    def module(self):
        return self.frame.f_globals.get('__name__', None)

    @CachedProperty
    def filename(self):
        filename = self.frame.f_globals.get('__file__', '')

        if filename.endswith(('.pyc', '.pyo')):
            filename = filename[:-1]
        elif filename.endswith('$py.class'):  # Jython
            filename = filename[:-9] + ".py"

        return filename

    @CachedProperty
    def lineno(self):
        return self.frame.f_lineno

    __getitem__ = object.__getattribute__


class F(Fields.query):
    """
    The ``F`` (ilter) expression.

    Allows inlined predicates (it will automatically expand to ``Or(...)``).
    """
    def __new__(cls, *predicates, **query):
        """
        Handles situations where :class:`hunter.F` objects (or other callables) are passed in as positional arguments. Conveniently converts
        that to an :class:`hunter.Or` predicate,
        """
        optional_actions = query.pop("actions", [])
        if "action" in query:
            optional_actions.append(query.pop("action"))

        if predicates:
            predicates += F(**query),
            result = Or(*predicates)
        else:
            result = F(**query) if optional_actions else super(F, cls).__new__(cls)

        if optional_actions:
            result = When(result, actions=optional_actions)

        return result

    def __init__(self, **query):
        """
        Args:
            query: criteria to match on. Currently only 'function', 'module' or 'filename' are accepted.
        """
        for key in query:
            if key not in ('function', 'module', 'filename'):
                raise TypeError("Unexpected argument {!r}. Must be one of 'function', 'module' or 'filename'.".format(key))
        self.query = query

    def __str__(self):
        return "F({})".format(
            ', '.join("{}={}".format(*item) for item in self.query.items()),
        )

    def __call__(self, event):
        """
        Handles event. Returns True if all criteria matched.
        """
        for key, value in self.query.items():
            if event[key] != value:
                return

        return True

    def __or__(self, other):
        """
        Convenience API so you can do ``F() | F()``. It converts that to ``Or(F(), F())``.
        """
        return Or(self, other)

    def __and__(self, other):
        """
        Convenience API so you can do ``F() & F()``. It converts that to ``And(F(), F())``.
        """
        return And(self, other)


class When(Fields.condition.actions):
    """
    Runs ``actions`` when ``condition(event)`` is ``True``.

    Actions take a single ``event`` argument.
    """
    def __init__(self, condition, actions):
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


class And(Fields.predicates):
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
                return
        return True

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(*chain(self.predicates, other.predicates if isinstance(other, And) else (other,)))


class Or(Fields.predicates):
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

    def __or__(self, other):
        return Or(*chain(self.predicates, other.predicates if isinstance(other, Or) else (other,)))

    def __and__(self, other):
        return And(self, other)


class Action(object):
    def __call__(self, event):
        raise NotImplementedError()


class Debugger(Fields.klass.kwargs, Action):
    """
    An action that starts ``pdb``.
    """
    def __init__(self, klass=pdb.Pdb, **kwargs):
        self.klass = klass
        self.kwargs = kwargs

    def __call__(self, event):
        """
        Runs a ``pdb.set_trace`` at the matching frame.
        """
        self.klass(**self.kwargs).set_trace(event.frame)


class CodePrinter(Fields.stream.filename_alignment, Action):
    """
    An action that just prints the code being executed.
    """
    def __init__(self, stream=sys.stderr, filename_alignment=DEFAULT_MIN_FILENAME_ALIGNMENT):
        self.stream = stream
        self.filename_alignment = filename_alignment

    def _getline(self, filename, lineno, getline=linecache.getline):
        """
        Get a line from ``linecache``. Ignores failures somewhat.
        """
        try:
            return getline(filename, lineno)
        except Exception as exc:
            return "??? no source: {} ???".format(exc)

    def __call__(self, event, basename=os.path.basename):
        """
        Handle event and print filename, line number and source code. If event.kind is a `return` or `exception` also prints values.
        """
        filename = event.filename or "<???>"
        # TODO: support auto-alignment, need a context object for this, eg:
        # alignment = context.filename_alignment = max(getattr(context, 'filename_alignment', self.filename_alignment), len(filename))
        self.stream.write("{:>{align}}:{:<5} {:9} {}\n".format(
            basename(filename),
            event.lineno,
            event.kind,
            self._getline(filename, event.lineno).rstrip(),
            align=self.filename_alignment
        ))
        if event.kind in ('return', 'exception'):
            self.stream.write("{:>{align}}       {:9} {} value: {!r}\n".format(
                "",
                "...",
                event.kind,
                event.arg,
                align=self.filename_alignment
            ))


class VarsPrinter(Fields.names.globals.stream.filename_alignment, Action):
    """
    An action that prints local variables and optinally global variables visible from the current executing frame.
    """
    def __init__(self, name=None, names=(), globals=False, stream=sys.stderr, filename_alignment=DEFAULT_MIN_FILENAME_ALIGNMENT):
        self.stream = stream
        self.filename_alignment = filename_alignment
        self.names = list(names)
        if name:
            self.names.append(name)
        self.globals = globals

    def __call__(self, event):
        """
        Handle event and print the specified variables.
        """
        first = True
        for key, value in event.locals.items():
            if key in self.names or not self.names:
                self.stream.write("{:>{align}}       {:9} {} -> {!r}\n".format(
                    "",
                    "vars" if first else "...",
                    key,
                    value,
                    align=self.filename_alignment
                ))
                first = False
        if self.globals:
            for key, value in event.globals.items():
                if key in self.names or not self.names:
                    self.stream.write("{:>{align}}       {:9} {} => {!r}\n".format(
                        "",
                        "vars" if first else "...",
                        key,
                        value,
                        align=self.filename_alignment
                    ))
                    first = False

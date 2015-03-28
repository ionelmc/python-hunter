from __future__ import absolute_import
from __future__ import unicode_literals

import ast
import atexit
import inspect
import linecache
import os
import pdb
import sys
from itertools import chain

from fields import Fields
from colorama import AnsiToWin32, Fore, Style


__version__ = "0.2.1"
__all__ = 'Q', 'When', 'And', 'Or', 'CodePrinter', 'Debugger', 'VarsPrinter', 'trace', 'stop'

DEFAULT_MIN_FILENAME_ALIGNMENT = 30
NO_COLORS = {
    'reset': '',
    'filename': '',
    'colon': '',
    'lineno': '',
    'kind': '',
    'continuation': '',
    'return': '',
    'exception': '',
    'detail': '',
    'vars': '',
    'call': '',
    'line': '',
}
EVENT_COLORS = {
    'reset': Style.RESET_ALL,
    'filename': '',
    'colon': Fore.BLACK + Style.BRIGHT,
    'lineno': Style.RESET_ALL,
    'kind': Fore.CYAN,
    'continuation': Fore.BLUE,
    'return': Style.BRIGHT + Fore.GREEN,
    'exception': Style.BRIGHT + Fore.RED,
    'detail': Style.NORMAL,
    'vars': Fore.MAGENTA,
}
CODE_COLORS = {
    'call': Fore.RESET + Style.BRIGHT,
    'line': Fore.RESET,
    'return': Fore.YELLOW,
    'exception': Fore.RED,
}


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
            predicates (:class:`hunter.Q` instances): Runs actions if any of the given predicates match.
            options: Keyword arguments that are passed to :class:`hunter.Q`, for convenience.
        """
        if "action" not in options and "actions" not in options:
            options["action"] = CodePrinter()
        merge = options.pop("merge", True)
        predicate = Q(*predicates, **options)

        previous_tracer = sys.gettrace()
        if previous_tracer is self and merge:
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
stop = atexit.register(_tracer.stop)


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
    frame = None
    kind = None
    arg = None

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
        return self.frame.f_globals.get('__name__', '')

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

    @CachedProperty
    def line(self, getline=linecache.getline):
        """
        Get a line from ``linecache``. Ignores failures somewhat.
        """
        try:
            return getline(self.filename, self.lineno)
        except Exception as exc:
            return "??? no source: {} ???".format(exc)

    __getitem__ = object.__getattribute__


def Q(*predicates, **query):
    """
    Handles situations where :class:`hunter.Query` objects (or other callables) are passed in as positional arguments.
    Conveniently converts that to an :class:`hunter.Or` predicate.
    """
    optional_actions = query.pop("actions", [])
    if "action" in query:
        optional_actions.append(query.pop("action"))

    if predicates:
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
    """
    query = ()
    allowed = tuple(i for i in Event.__dict__.keys() if not i.startswith('_'))

    def __init__(self, **query):
        """
        Args:
            query: criteria to match on. Currently only 'function', 'module' or 'filename' are accepted.
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
            if event[key] != value:
                return

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


class And(Fields.predicates):
    """
    `And` predicate. Exits at the first sub-predicate that returns ``False``.
    """
    def __new__(cls, *predicates):
        if not predicates:
            raise TypeError("Expected at least 2 predicates.")
        elif len(predicates) == 1:
            return predicates[0]
        else:
            return super(And, cls).__new__(cls)

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
    def __new__(cls, *predicates):
        if not predicates:
            raise TypeError("Expected at least 2 predicates.")
        elif len(predicates) == 1:
            return predicates[0]
        else:
            return super(Or, cls).__new__(cls)

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


class ColorStreamAction(Action):
    _stream = None
    _tty = None

    @property
    def stream(self):
        return self._stream

    @stream.setter
    def stream(self, value):
        isatty = getattr(value, 'isatty', None)
        if isatty and isatty():
            self._stream = AnsiToWin32(value)
            self._tty = True
            self.event_colors = EVENT_COLORS
            self.code_colors = CODE_COLORS
        else:
            self._tty = False
            self._stream = value
            self.event_colors = NO_COLORS
            self.code_colors = NO_COLORS


class CodePrinter(Fields.stream.filename_alignment, ColorStreamAction):
    """
    An action that just prints the code being executed.

    Args:
        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filaname column (files are right-aligned). Default: ``15``.
    """
    def __init__(self, stream=sys.stderr, filename_alignment=DEFAULT_MIN_FILENAME_ALIGNMENT):
        self.stream = stream
        self.filename_alignment = filename_alignment

    def __call__(self, event, sep=os.path.sep, join=os.path.join):
        """
        Handle event and print filename, line number and source code. If event.kind is a `return` or `exception` also prints values.
        """
        filename = event.filename or "<???>"
        # TODO: support auto-alignment, need a context object for this, eg:
        # alignment = context.filename_alignment = max(getattr(context, 'filename_alignment', self.filename_alignment), len(filename))
        self.stream.write("{filename}{:>{align}}{colon}:{lineno}{:<5} {kind}{:9} {code}{}{reset}\n".format(
            join(*filename.split(sep)[-2:]),
            event.lineno,
            event.kind,
            event.line.rstrip(),
            align=self.filename_alignment,
            code=self.code_colors[event.kind],
            **self.event_colors
        ))
        if event.kind in ('return', 'exception'):
            self.stream.write("{:>{align}}       {continuation}{:9} {color}{} value: {detail}{!r}{reset}\n".format(
                "",
                "...",
                event.kind,
                event.arg,
                align=self.filename_alignment,
                color=self.event_colors[event.kind],
                **self.event_colors
            ))


class VarsPrinter(Fields.names.globals.stream.filename_alignment, ColorStreamAction):
    """
    An action that prints local variables and optionally global variables visible from the current executing frame.

    Args:
        *names (strings):
            Names to evaluate. Expressions can be used (will only try to evaluate if all the variables are present on the frame.
        stream (file-like): Stream to write to. Default: ``sys.stderr``.
        filename_alignment (int): Default size for the filaneme column (files are right-aligned). Default: ``15``.
        globals (bool): Allow access to globals. Default: ``False`` (only looks at locals).
    """
    default_stream = sys.stderr

    def __init__(self, *names, **options):
        if not names:
            raise TypeError("Must give at least one name/expression.")
        self.stream = options.pop('stream', self.default_stream)
        self.filename_alignment = options.pop('filename_alignment', DEFAULT_MIN_FILENAME_ALIGNMENT)
        self.names = {
            name: set(self._iter_symbols(name))
            for name in names
        }
        self.globals = options.pop('globals', False)

    @staticmethod
    def _iter_symbols(code):
        """
        Iterate all the variable names in the given expression.

        Example:

        * ``self.foobar`` yields ``self``
        * ``self[foobar]`` yields `self`` and ``foobar``
        """
        for node in ast.walk(ast.parse(code)):
            if isinstance(node, ast.Name):
                yield node.id

    def _safe_eval(self, code, event):
        """
        Try to evaluate the given code on the given frame. If failure occurs, returns some ugly string with exception.
        """
        try:
            return eval(code, event.globals if self.globals else {}, event.locals)
        except Exception as exc:
            return "{exception}FAILED EVAL: {}".format(exc, **self.event_colors)

    def __call__(self, event):
        """
        Handle event and print the specified variables.
        """
        first = True
        frame_symbols = set(event.locals)
        if self.globals:
            frame_symbols |= set(event.globals)

        for code, symbols in self.names.items():
            if frame_symbols >= symbols:
                self.stream.write("{:>{align}}       {vars}{:9} {reset}{} {vars}=> {reset}{!r}\n".format(
                    "",
                    "vars" if first else "...",
                    code,
                    self._safe_eval(code, event),
                    align=self.filename_alignment,
                    **self.event_colors
                ))
                first = False

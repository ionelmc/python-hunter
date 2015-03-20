import inspect
import sys

from fields import Fields

from hunter.actions import Action
from hunter.actions import CodePrinter
from hunter.actions import Debugger
from hunter.actions import VarsDumper


__version__ = "0.1.0"


class Tracer(Fields.predicate):
    """
    Trace object.

    """

    def __init__(self):
        self._current_predicate = self.not_started
        self._previous_tracer = None

    def not_started(self, _):
        raise RuntimeError("Tracer is not started.")

    def __call__(self, frame, kind, arg):
        """
        The settrace function.

        .. note::

            This always returns self (drills down) - as opposed to only drilling down when predicate(event) is True because it might
            match further inside.
        """
        self.predicate(Event(frame, kind, arg))
        if self._previous_tracer:
            self._previous_tracer(frame, kind, arg)
        return self

    def trace(self, *predicates, **options):
        """
        Starts tracing. Can be used as a context manager (with slightly incorrect semantics - it starts tracing before ``__enter__`` is
        called).
        """
        if "action" not in options:
            options["action"] = CodePrinter()
        predicate = F(*predicates, **options)

        previous_tracer = sys.gettrace()
        if previous_tracer is self:
            self._current_predicate |= predicate
        else:
            self._previous_tracer = previous_tracer
            sys.settrace(self)
        return self

    def stop(self):
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
        return self.frame.f_globals.get('__file__', None)

    @CachedProperty
    def lineno(self):
        return self.frame.f_lineno

    __getitem__ = object.__getattribute__


class F(Fields.query):
    """
    The ``F``(ilter) expression.

    Allows inlined predicates (it will automatically expand to ``Or(...)``).
    """
    def __new__(cls, *predicates, **query):
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
        for key in query:
            if key not in ('function', 'module', 'filename'):
                raise TypeError("Unexpected argument {!r}. Must be one of 'function', 'module' or 'filename'.".format(key))
        self.query = query

    def __str__(self):
        return "F({})".format(
            ', '.join("{}={}".format(*item) for item in self.query.items()),
        )

    def __call__(self, event):
        for key, value in self.query.items():
            if event[key] != value:
                return

        return True

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
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
        if self.condition(event):
            for action in self.actions:
                action(event)

            return True


class And(Fields.predicates):
    """
    `And` predicate. Exits at the first sub-predicate that returns ``False``.
    """
    def __init__(self, *predicates):
        self.predicates = predicates

    def __str__(self):
        return "And({})".format(', '.join(str(p) for p in self.predicates))

    def __call__(self, event):
        for predicate in self.predicates:
            if not predicate(event):
                return
        return True


class Or(Fields.predicates):
    """
    `Or` predicate. Exits at first sub-predicate that returns ``True``.
    """
    def __init__(self, *predicates):
        self.predicates = predicates

    def __call__(self, event):
        for predicate in self.predicates:
            if predicate(event):
                return True


if __name__ == '__main__':
    trace(actions=[CodePrinter(), VarsDumper(names=['a', 'b'])])

    def foo(*x):
        #print(x)
        a = 1 + 2
        b = 3
        try:
            raise Exception('BOOM!')
        finally:
            return x

    foo(1, 2, 3)

from __future__ import absolute_import

import atexit
import functools
import inspect
import os
import weakref

from .actions import Action
from .actions import CallPrinter
from .actions import CodePrinter
from .actions import Debugger
from .actions import Manhole
from .actions import VarsPrinter
from .actions import VarsSnooper
from .config import THREADING_SUPPORT_ALIASES
from .config import load_config

try:
    if os.environ.get("PUREPYTHONHUNTER"):
        raise ImportError("Cython speedups are disabled.")

    from ._event import Event
    from ._predicates import And as _And
    from ._predicates import From as _From
    from ._predicates import Not as _Not
    from ._predicates import Or as _Or
    from ._predicates import When
    from ._predicates import Query
    from ._tracer import Tracer
except ImportError:
    from .event import Event  # noqa
    from .predicates import And as _And
    from .predicates import From as _From
    from .predicates import Not as _Not
    from .predicates import Or as _Or
    from .predicates import When
    from .predicates import Query
    from .tracer import Tracer


try:
    from ._version import version as __version__
except ImportError:
    __version__ = "3.0.1"

__all__ = (
    "And",
    "CallPrinter",
    "CodePrinter",
    "Debugger",
    "From",
    "Manhole",
    "Not",
    "Or",
    "Q",
    "Query",
    "VarsPrinter",
    "VarsSnooper",
    "When",
    "stop",
    "trace",
)
_last_tracer = None
_default_config = {}


def Q(*predicates, **query):
    """
    Helper that handles situations where :class:`hunter.predicates.Query` objects (or other callables)
    are passed in as positional arguments - it conveniently converts those to a
    :class:`hunter.predicates.And` predicate.
    """
    optional_actions = query.pop("actions", [])
    if "action" in query:
        optional_actions.append(query.pop("action"))

    for p in predicates:
        if not callable(p):
            raise TypeError("Predicate {0!r} is not callable.".format(p))

    for a in optional_actions:
        if not callable(a):
            raise TypeError("Action {0!r} is not callable.".format(a))

    if predicates:
        predicates = tuple(
            p() if inspect.isclass(p) and issubclass(p, Action) else p
            for p in predicates
        )
        if any(isinstance(p, (CallPrinter, CodePrinter)) for p in predicates):
            # the user provided an action as a filter, remove the action then to prevent double output
            for action in optional_actions:
                if action in (CallPrinter, CodePrinter) or isinstance(
                    action, (CallPrinter, CodePrinter)
                ):
                    optional_actions.remove(action)
        if query:
            predicates += (Query(**query),)

        result = And(*predicates)
    else:
        result = Query(**query)

    if optional_actions:
        result = When(result, *optional_actions)

    return result


def _flatten(cls, predicate, *predicates):
    if not predicates:
        return predicate
    else:
        all_predicates = []
        if isinstance(predicate, cls):
            all_predicates.extend(predicate.predicates)
        else:
            all_predicates.append(predicate)

        for p in predicates:
            if isinstance(p, cls):
                all_predicates.extend(p.predicates)
            else:
                all_predicates.append(p)
        return cls(*all_predicates)


def And(*predicates, **kwargs):
    """
    Helper that flattens out ``predicates`` in a single :class:`hunter.predicates.And` object if possible.
    As a convenience it converts ``kwargs`` to a single :class:`hunter.predicates.Query` instance.

    Args:
        *predicates (callables): Callables that returns True/False or :class:`hunter.predicates.Query` objects.
        **kwargs: Arguments that may be passed to :class:`hunter.predicates.Query`

    Returns: A :class:`hunter.predicates.And` instance.

    """
    if kwargs:
        predicates += (Query(**kwargs),)
    return _flatten(_And, *predicates)


def Or(*predicates, **kwargs):
    """
    Helper that flattens out ``predicates`` in a single :class:`hunter.predicates.Or` object if possible.
    As a convenience it converts ``kwargs`` to multiple :class:`hunter.predicates.Query` instances.

    Args:
        *predicates (callables): Callables that returns True/False or :class:`hunter.predicates.Query` objects.
        **kwargs: Arguments that may be passed to :class:`hunter.predicates.Query`.

    Returns: A :class:`hunter.predicates.Or` instance.

    """
    if kwargs:
        predicates += tuple(Query(**{k: v}) for k, v in kwargs.items())
    return _flatten(_Or, *predicates)


def Not(*predicates, **kwargs):
    """
    Helper that flattens out ``predicates`` in a single :class:`hunter.predicates.And` object if possible.
    As a convenience it converts ``kwargs`` to multiple :class:`hunter.predicates.Query` instances.

    Args:
        *predicates (callables): Callables that returns True/False or :class:`hunter.predicates.Query` objects.
        **kwargs: Arguments that may be passed to :class:`hunter.predicates.Query`.

    Returns: A :class:`hunter.predicates.Not` instance (possibly containing a :class:`hunter.predicates.And` instance).
    """
    if kwargs:
        predicates += (Query(**kwargs),)
    if len(predicates) > 1:
        return _Not(_flatten(_And, *predicates))
    else:
        return _Not(*predicates)


def From(predicate=None, condition=None, watermark=0, **kwargs):
    """
    Helper that converts keyword arguments to a ``From(Q(**kwargs))``.

    Args:
        condition (callable): A callable that returns True/False or a :class:`hunter.predicates.Query` object.
        predicate (callable): Optional callable that returns True/False or a :class:`hunter.predicates.Query` object to
            run after ``condition`` first returns ``True``.
        watermark (int): Depth difference to switch off and wait again on ``condition``.
        **kwargs: Arguments that are passed to :func:`hunter.Q`
    """
    if predicate is None and condition is None and watermark == 0:
        return _From(Q(**kwargs))
    else:
        if kwargs:
            raise TypeError(
                "Unexpected arguments {}. Don't combine positional with keyword arguments.".format(
                    kwargs.keys()
                )
            )
        return _From(predicate, condition, watermark)


def stop():
    """
    Stop tracing. Restores previous tracer (if there was any).
    """
    global _last_tracer

    if _last_tracer is not None:
        _last_tracer.stop()
        _last_tracer = None


class Stop(Action):
    def __call__(self, event):
        stop()


def _prepare_predicate(*predicates, **options):
    if "action" not in options and "actions" not in options:
        options["action"] = CallPrinter

    return Q(*predicates, **options)


def trace(*predicates, **options):
    """
    Starts tracing. Can be used as a context manager (with slightly incorrect semantics - it starts tracing
    before ``__enter__`` is called).

    Parameters:
        *predicates (callables): Runs actions if **all** of the given predicates match.
    Keyword Args:
        clear_env_var: Disables tracing in subprocess. Default: ``False``.
        threading_support: Enable tracing *new* threads. Default: ``None``.

            Modes:

            - ``None`` - automatic (enabled but actions only prefix with thread name if more than 1 thread)
            - ``False`` - completely disabled
            - ``True`` - enabled (actions always prefix with thread name)

            You can also use:
            ``threads_support``, ``thread_support``, ``threadingsupport``, ``threadssupport``, ``threadsupport``,
            ``threading``, ``threads`` or ``thread``.
        action: Action to run if all the predicates return ``True``. Default: ``CodePrinter``.
        actions: Actions to run (in case you want more than 1).
        **kwargs: for convenience you can also pass anything that you'd pass to :obj:`hunter.Q`
    """
    global _last_tracer

    predicates, options = load_config(predicates, options)

    clear_env_var = options.pop("clear_env_var", False)
    threading_support = None
    for alias in THREADING_SUPPORT_ALIASES:
        if alias in options:
            threading_support = options.pop(alias)
    predicate = _prepare_predicate(*predicates, **options)

    if clear_env_var:
        os.environ.pop("PYTHONHUNTER", None)

    _last_tracer = Tracer(threading_support)

    @atexit.register
    def atexit_cleanup(ref=weakref.ref(_last_tracer)):
        maybe_tracer = ref()
        if maybe_tracer is not None:
            maybe_tracer.stop()

    return _last_tracer.trace(predicate)


def wrap(function_to_trace=None, **trace_options):
    """
    Functions decorated with this will be traced.

    Use ``local=True`` to only trace local code, eg::

        @hunter.wrap(local=True)
        def my_function():
            ...

    Keyword arguments are allowed, eg::

        @hunter.wrap(action=hunter.CallPrinter)
        def my_function():
            ...

    Or, filters::

        @hunter.wrap(module='foobar')
        def my_function():
            ...
    """

    def tracing_decorator(func):
        @functools.wraps(func)
        def tracing_wrapper(*args, **kwargs):
            predicates = []
            local = trace_options.pop("local", False)
            if local:
                predicates.append(Query(depth_lt=2))
            predicates.append(
                From(
                    Query(kind="call"),
                    Not(
                        When(
                            Query(calls_gt=0, depth=0) & Not(Query(kind="return")), Stop
                        )
                    ),
                    watermark=-1,
                )
            )
            local_tracer = trace(*predicates, **trace_options)
            try:
                return func(*args, **kwargs)
            finally:
                local_tracer.stop()

        return tracing_wrapper

    if function_to_trace is None:
        return tracing_decorator
    else:
        return tracing_decorator(function_to_trace)

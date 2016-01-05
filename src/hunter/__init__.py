from __future__ import absolute_import

import atexit
import inspect
import os
from functools import partial

from .actions import Action
from .actions import CodePrinter
from .actions import Debugger
from .actions import VarsPrinter

try:
    if os.environ.get("PUREPYTHONHUNTER"):
        raise ImportError("Skipped")

    from ._predicates import And as _And
    from ._predicates import Not
    from ._predicates import Or as _Or
    from ._predicates import When
    from ._predicates import Query
    from ._tracer import Tracer
except ImportError:
    from .predicates import And as _And
    from .predicates import Not
    from .predicates import Or as _Or
    from .predicates import When
    from .predicates import Query
    from .tracer import Tracer

__version__ = "1.0.2"
__all__ = (
    'And',
    'CodePrinter',
    'Debugger',
    'Not',
    'Or',
    'Q',
    'Query',
    'stop',
    'trace',
    'VarsPrinter',
    'When',
)


def Q(*predicates, **query):
    """
    Handles situations where :class:`hunter.Query` objects (or other callables) are passed in as positional arguments.
    Conveniently converts that to an :class:`hunter.And` predicate.
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

        result = And(*predicates)
    else:
        result = Query(**query)

    if optional_actions:
        result = When(result, *optional_actions)

    return result


def _flatten(predicate, *predicates, **kwargs):
    cls = kwargs.pop('cls')
    if kwargs:
        raise TypeError("Did not expecte keyword arguments")

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


And = partial(_flatten, cls=_And)
Or = partial(_flatten, cls=_Or)

_current_tracer = None


def stop():
    """
    Stop tracing.

    Notes:
        Restores previous tracer (if there was any).
    """
    global _current_tracer

    if _current_tracer is not None:
        _current_tracer.stop()
        _current_tracer = None


def _prepare_predicate(*predicates, **options):
    if "action" not in options and "actions" not in options:
        options["action"] = CodePrinter

    return Q(*predicates, **options)


def trace(*predicates, **options):
    """
    Starts tracing. Can be used as a context manager (with slightly incorrect semantics - it starts tracing
    before ``__enter__`` is called).

    Parameters:
        *predicates (callables): Runs actions if any of the given predicates match.
    Keyword Args:
        clear_env_var: Disables tracing in subprocess. Default: ``False``.
        action: Action to run if all the predicates return ``True``. Default: ``CodePrinter``.
        actions: Actions to run (in case you want more than 1).
    """
    global _current_tracer

    predicate = _prepare_predicate(*predicates, **options)
    clear_env_var = options.pop("clear_env_var", False)

    if clear_env_var:
        os.environ.pop("PYTHONHUNTER", None)
    try:
        _current_tracer = Tracer()
        return _current_tracer.trace(predicate)
    finally:
        atexit.register(_current_tracer.stop)

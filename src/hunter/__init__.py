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
    from ._predicates import And as _And
    from ._predicates import Or as _Or
    from ._predicates import When
    from ._predicates import Query
    from ._tracer import Tracer
except ImportError:
    from .predicates import And as _And
    from .predicates import Or as _Or
    from .predicates import When
    from .predicates import Query
    from .tracer import Tracer



__version__ = "0.6.0"
__all__ = 'Q', 'When', 'And', 'Or', 'CodePrinter', 'Debugger', 'VarsPrinter', 'trace', 'stop'


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

_tracer = Tracer()

def trace(*predicates, **options):
    if "action" not in options and "actions" not in options:
        options["action"] = CodePrinter

    merge = options.pop("merge", True)
    clear_env_var = options.pop("clear_env_var", False)
    predicate = Q(*predicates, **options)

    if clear_env_var:
        os.environ.pop("PYTHONHUNTER", None)

    _tracer.trace(predicate, merge)

stop = atexit.register(_tracer.stop)


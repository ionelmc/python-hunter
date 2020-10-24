from __future__ import absolute_import

import atexit
import functools
import inspect
import os
import sys
import warnings
import weakref

from .actions import Action
from .actions import CallPrinter
from .actions import CodePrinter
from .actions import Debugger
from .actions import ErrorSnooper
from .actions import Manhole
from .actions import StackPrinter
from .actions import VarsPrinter
from .actions import VarsSnooper

try:
    if os.environ.get('PUREPYTHONHUNTER'):
        raise ImportError('Cython speedups are disabled.')

    from ._event import Event
    from ._predicates import And as _And
    from ._predicates import Backlog as _Backlog
    from ._predicates import From as _From
    from ._predicates import Not as _Not
    from ._predicates import Or as _Or
    from ._predicates import Query
    from ._predicates import When
    from ._tracer import Tracer
except ImportError:
    from .event import Event  # noqa
    from .predicates import And as _And
    from .predicates import Backlog as _Backlog
    from .predicates import From as _From
    from .predicates import Not as _Not
    from .predicates import Or as _Or
    from .predicates import Query
    from .predicates import When
    from .tracer import Tracer

try:
    from ._version import version as __version__
except ImportError:
    __version__ = '3.3.1'

__all__ = (
    'And',
    'Backlog',
    'CallPrinter',
    'CodePrinter',
    'Debugger',
    'ErrorSnooper',
    'From',
    'Manhole',
    'Not',
    'Or',
    'Q',
    'Query',
    'StackPrinter',
    'VarsPrinter',
    'VarsSnooper',
    'When',
    'Backlog',

    'stop',
    'trace',
)
THREADING_SUPPORT_ALIASES = (
    'threading_support', 'threads_support', 'thread_support',
    'threadingsupport', 'threadssupport', 'threadsupport',
    'threading', 'threads', 'thread',
)
TRACER_OPTION_NAMES = THREADING_SUPPORT_ALIASES + (
    'clear_env_var',
    'profile',
)
_last_tracer = None
_default_trace_args = None
_default_config = {}
_default_stream = sys.stderr


def _prepare_config(*args, **kwargs):
    _default_config.clear()
    _default_config.update((key.lower(), val) for key, val in kwargs.items())
    options = {}
    predicates = []

    for key, value in list(_default_config.items()):
        if key in TRACER_OPTION_NAMES:
            options[key] = _default_config.pop(key)
            continue
        elif key in (
            # builtin actions config
            'klass',
            'stream',
            'force_colors',
            'force_pid',
            'filename_alignment',
            'thread_alignment',
            'pid_alignment',
            'repr_limit',
            'repr_func',
        ):
            continue

        try:
            Q(**{key: value})
        except TypeError:
            pass
        else:
            options[key] = _default_config.pop(key)
            continue

        _default_config.pop(key)
        sys.stderr.write('Discarded config from PYTHONHUNTERCONFIG {}={!r}: Unknown option\n'.format(
            key, value))
    for position, predicate in enumerate(args):
        if callable(predicate):
            predicates.append(predicate)
        else:
            sys.stderr.write('Discarded config from PYTHONHUNTERCONFIG {} (position {}): Not a callable\n'.format(
                predicate, position))

    return predicates, options


def Q(*predicates, **query):
    """
    Helper that handles situations where :class:`hunter.predicates.Query` objects (or other callables)
    are passed in as positional arguments - it conveniently converts those to a
    :class:`hunter.predicates.And` predicate.

    See Also:
         :class:`hunter.predicates.Query`
    """
    optional_actions = query.pop('actions', [])
    if 'action' in query:
        optional_actions.append(query.pop('action'))

    for p in predicates:
        if not callable(p):
            raise TypeError('Predicate {0!r} is not callable.'.format(p))

    for a in optional_actions:
        if not callable(a):
            raise TypeError('Action {0!r} is not callable.'.format(a))

    if predicates:
        predicates = tuple(
            p() if inspect.isclass(p) and issubclass(p, Action) else p
            for p in predicates
        )
        if any(isinstance(p, (CallPrinter, CodePrinter)) for p in predicates):
            # the user provided an action as a filter, remove the action then to prevent double output
            for action in optional_actions:
                if action in (CallPrinter, CodePrinter) or isinstance(action, (CallPrinter, CodePrinter)):
                    optional_actions.remove(action)
        if query:
            predicates += Query(**query),

        result = And(*predicates)
    else:
        result = Query(**query)

    if optional_actions:
        result = When(result, *optional_actions)

    return result


def _merge(*predicates, **query):
    if predicates:
        if query:
            predicates += Query(**query),
        return And(*predicates)
    else:
        return Query(**query)


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
        **kwargs: Arguments that may be passed to :class:`hunter.predicates.Query`.

    Returns: A :class:`hunter.predicates.And` instance.

    See Also:
         :class:`hunter.predicates.And`
    """
    if kwargs:
        predicates += Query(**kwargs),
    return _flatten(_And, *predicates)


def Or(*predicates, **kwargs):
    """
    Helper that flattens out ``predicates`` in a single :class:`hunter.predicates.Or` object if possible.
    As a convenience it converts ``kwargs`` to multiple :class:`hunter.predicates.Query` instances.

    Args:
        *predicates (callables): Callables that returns True/False or :class:`hunter.predicates.Query` objects.
        **kwargs: Arguments that may be passed to :class:`hunter.predicates.Query`.

    Returns: A :class:`hunter.predicates.Or` instance.

    See Also:
         :class:`hunter.predicates.Or`
    """
    if kwargs:
        predicates += tuple(Query(**{key: value}) for key, value in kwargs.items())
    return _flatten(_Or, *predicates)


def Not(*predicates, **kwargs):
    """
    Helper that flattens out ``predicates`` in a single :class:`hunter.predicates.And` object if possible.
    As a convenience it converts ``kwargs`` to multiple :class:`hunter.predicates.Query` instances.

    Args:
        *predicates (callables): Callables that returns True/False or :class:`hunter.predicates.Query` objects.
        **kwargs: Arguments that may be passed to :class:`hunter.predicates.Query`.

    Returns: A :class:`hunter.predicates.Not` instance (possibly containing a :class:`hunter.predicates.And` instance).

    See Also:
         :class:`hunter.predicates.Not`
    """
    if kwargs:
        predicates += Query(**kwargs),
    if len(predicates) > 1:
        return _Not(_flatten(_And, *predicates))
    else:
        return _Not(*predicates)


def From(condition=None, predicate=None, watermark=0, **kwargs):
    """
    Helper that converts keyword arguments to ``From(condition=Q(**normal_kwargs), predicate=Q(**rel_kwargs)``
    where ``rel_kwargs`` are all the kwargs that start with "depth" or "calls".

    Args:
        condition (callable): A callable that returns True/False or a :class:`hunter.predicates.Query` object.
        predicate (callable): Optional callable that returns True/False or a :class:`hunter.predicates.Query` object to
            run after ``condition`` first returns ``True``.
        **kwargs: Arguments that are passed to :func:`hunter.Q`. Any kwarg that starts with "depth" or "calls" will be included `predicate`.

    Examples:
        ``From(function='foobar', depth_lt=5)`` coverts to ``From(Q(function='foobar'), Q(depth_lt=5))``.
        The depth filter is moved in the predicate because it would not have any effect as a condition - it stop being called after it
        returns True, thus it doesn't have the intended effect (a limit to how deep to trace from ``foobar``).

    See Also:
         :class:`hunter.predicates.From`
    """
    if predicate is None and condition is None:
        condition_kwargs = {key: value for key, value in kwargs.items() if not key.startswith('depth') and not key.startswith('calls')}
        predicate_kwargs = {key: value for key, value in kwargs.items() if key.startswith('depth') or key.startswith('calls')}
        return _From(Q(**condition_kwargs), Q(**predicate_kwargs), watermark)
    else:
        if kwargs:
            raise TypeError("Unexpected arguments {}. Don't combine positional with keyword arguments.".format(
                kwargs.keys()))
        return _From(condition, predicate, watermark)


def Backlog(*conditions, **kwargs):
    """
    Helper that merges kwargs and conditions prior to creating the :class:`~hunter.predicates.Backlog`.

    Args:
        *conditions (callable): Optional :class:`~hunter.predicates.Query` object or a callable that returns True/False.
        size (int): Number of events that the backlog stores. Effectively this is the ``maxlen`` for the internal deque.
        stack (int): Stack size to fill. Setting this to ``0`` disables creating fake call events.
        vars (bool): Makes global/local variables available in the stored events.
            This is an expensive option - it will use ``action.try_repr`` on all the variables.
        strip (bool): If this option is set then the backlog will be cleared every time an event matching the ``condition`` is found.
            Disabling this may show more context every time an event matching the ``condition`` is found but said context may also be
            duplicated across multiple matches.
        action (ColorStreamAction): A ColorStreamAction to display the stored events when an event matching the ``condition`` is found.
        filter (callable): Optional :class:`~hunter.predicates.Query` object or a callable that returns True/False to filter the stored
            events with.
        **kwargs: Arguments that are passed to :func:`hunter.Q`. Any kwarg that starts with "depth" or "calls" will be included `predicate`.

    See Also:
         :class:`hunter.predicates.Backlog`
    """
    action = kwargs.pop('action', CallPrinter)
    filter = kwargs.pop('filter', None)
    size = kwargs.pop('size', 100)
    stack = kwargs.pop('stack', 10)
    strip = kwargs.pop('strip', True)
    vars = kwargs.pop('vars', False)
    if not conditions and not kwargs:
        raise TypeError('Backlog needs at least 1 condition '
                        "(it doesn't have any effect without one besides making everything incredibly slow).")
    return _Backlog(_merge(*conditions, **kwargs), size=size, stack=stack, vars=vars, strip=strip, action=action, filter=filter)


def stop():
    """
    Stop tracing. Restores previous tracer (if there was any).
    """
    global _last_tracer

    if _last_tracer is None:
        warnings.warn('There is no tracer to stop.')
    else:
        _last_tracer.stop()
        _last_tracer = None


class Stop(Action):
    def __call__(self, event):
        stop()


def _prepare_predicate(*predicates, **options):
    if 'action' not in options and 'actions' not in options:
        options['action'] = CallPrinter

    return Q(*predicates, **options)


def _apply_config(predicates, options):
    if _default_trace_args is None:
        return predicates, options
    else:
        config_predicates, config_options = _default_trace_args
        return predicates + tuple(config_predicates), dict(config_options, **options)


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

    See Also:
         :class:`hunter.tracer.Tracer` or :class:`hunter.event.Event`
    """
    global _last_tracer

    predicates, options = _apply_config(predicates, options)

    clear_env_var = options.pop('clear_env_var', False)
    profiling_mode = options.pop('profile', False)
    threading_support = None
    for alias in THREADING_SUPPORT_ALIASES:
        if alias in options:
            threading_support = options.pop(alias)
    predicate = _prepare_predicate(*predicates, **options)

    if clear_env_var:
        os.environ.pop('PYTHONHUNTER', None)

    _last_tracer = Tracer(threading_support, profiling_mode)

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
            local = trace_options.pop('local', False)
            if local:
                predicates.append(Query(depth_lt=2))
            predicates.append(
                From(
                    Query(kind='call'),
                    Not(When(
                        Query(calls_gt=0, depth=0) & Not(Query(kind='return')),
                        Stop
                    )),
                    watermark=-1
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


def load_config(*args, **kwargs):
    global _default_trace_args
    try:
        if args or kwargs:
            _default_trace_args = _prepare_config(*args, **kwargs)
        else:
            _default_trace_args = eval('_prepare_config({})'.format(os.environ.get('PYTHONHUNTERCONFIG', '')))
    except Exception as exc:
        sys.stderr.write('Failed to load hunter config from PYTHONHUNTERCONFIG {[PYTHONHUNTERCONFIG]!r}: {!r}\n'.format(
            os.environ, exc))
        _default_trace_args = (), ()


load_config()

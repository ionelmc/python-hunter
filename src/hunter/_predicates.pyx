# cython: linetrace=True, language_level=3str, c_api_binop_methods=True, freethreading_compatible=True
from __future__ import absolute_import

from collections import deque
from inspect import isclass
from re import compile as re_compile

cimport cython

from ._event cimport Event
from ._event cimport fast_clone
from ._event cimport fast_detach
from ._tracer cimport *

from .actions import Action
from .actions import ColorStreamAction

__all__ = (
    'And',
    'From',
    'Not',
    'Or',
    'Query',
    'When',
)

cdef tuple ALLOWED_KEYS = (
    'function', 'module', 'lineno', 'globals', 'stdlib', 'arg', 'locals', 'kind', 'filename', 'source',
    'fullsource', 'threadname', 'threadid', 'instruction', 'depth', 'calls', 'builtin',
)
cdef tuple ALLOWED_OPERATORS = (
    'startswith', 'endswith', 'in', 'contains', 'regex',
    'sw', 'ew', 'has', 'rx',
    'gt', 'gte', 'lt', 'lte',
)

ctypedef object (*Event_getter_typedef)(Event)
cdef inline Event_get_function(Event event): return event.function_getter()
cdef inline Event_get_module(Event event): return event.module_getter()
cdef inline Event_get_lineno(Event event): return event.lineno_getter()
cdef inline Event_get_globals(Event event): return event.globals_getter()
cdef inline Event_get_stdlib(Event event): return event.stdlib_getter()
cdef inline Event_get_arg(Event event): return event.arg
cdef inline Event_get_locals(Event event): return event.locals_getter()
cdef inline Event_get_kind(Event event): return event.kind
cdef inline Event_get_filename(Event event): return event.filename_getter()
cdef inline Event_get_source(Event event): return event.source_getter()
cdef inline Event_get_fullsource(Event event): return event.fullsource_getter()
cdef inline Event_get_threadname(Event event): return event.threadname_getter()
cdef inline Event_get_threadid(Event event): return event.threadid_getter()
cdef inline Event_get_instruction(Event event): return event.instruction_getter()
cdef inline Event_get_depth(Event event): return event.depth
cdef inline Event_get_calls(Event event): return event.calls
cdef inline Event_get_builtin(Event event): return event.builtin

cdef Event_getter_typedef[17] Event_getters = [
    Event_get_function,
    Event_get_module,
    Event_get_lineno,
    Event_get_globals,
    Event_get_stdlib,
    Event_get_arg,
    Event_get_locals,
    Event_get_kind,
    Event_get_filename,
    Event_get_source,
    Event_get_fullsource,
    Event_get_threadname,
    Event_get_threadid,
    Event_get_instruction,
    Event_get_depth,
    Event_get_calls,
    Event_get_builtin,
]


@cython.final
cdef class QueryEntry:
    cdef Event_getter_typedef getter
    cdef int getter_index
    cdef object value

    def __init__(self, object value, str name):
        self.value = value
        self.getter_index = ALLOWED_KEYS.index(name)
        self.getter = Event_getters[self.getter_index]

    def __repr__(self):
        return repr(self.value)

    def __eq__(self, other):
        return (
            isinstance(other, QueryEntry)
            and self.value == (<QueryEntry> other).value
            and self.getter_index == (<QueryEntry> other).getter_index
        )


@cython.final
cdef class Query:
    """
    A query class.

    See :class:`hunter.event.Event` for fields that can be filtered on.
    """
    def __init__(self, **query):
        """
        Args:
            query: criteria to match on.

                Accepted arguments:
                ``arg``,
                ``calls``,
                ``code``,
                ``depth``,
                ``filename``,
                ``frame``,
                ``fullsource``,
                ``function``,
                ``globals``,
                ``kind``,
                ``lineno``,
                ``locals``,
                ``module``,
                ``source``,
                ``stdlib``,
                ``threadid``,
                ``threadname``.
        """
        query_eq = {}
        query_startswith = {}
        query_endswith = {}
        query_in = {}
        query_contains = {}
        query_regex = {}
        query_lt = {}
        query_lte = {}
        query_gt = {}
        query_gte = {}

        for key, value in query.items():
            parts = [p for p in key.split('_') if p]
            count = len(parts)
            if count > 2:
                raise TypeError(
                    f'Unexpected argument {key!r}. Must be one of {ALLOWED_KEYS} with optional operators like: {ALLOWED_OPERATORS}'
                )
            elif count == 2:
                prefix, operator = parts
                if operator in ('startswith', 'sw'):
                    if not isinstance(value, basestring):
                        if not isinstance(value, (list, set, tuple)):
                            raise ValueError(f'Value {value!r} for {key!r} is invalid. Must be a string, list, tuple or set.')
                        value = tuple(value)
                    mapping = query_startswith
                elif operator in ('endswith', 'ew'):
                    if not isinstance(value, basestring):
                        if not isinstance(value, (list, set, tuple)):
                            raise ValueError(f'Value {value!r} for {key!r} is invalid. Must be a string, list, tuple or set.')
                        value = tuple(value)
                    mapping = query_endswith
                elif operator == 'in':
                    mapping = query_in
                elif operator in ('contains', 'has'):
                    mapping = query_contains
                elif operator in ('regex', 'rx'):
                    value = re_compile(value)
                    mapping = query_regex
                elif operator == 'lt':
                    mapping = query_lt
                elif operator == 'lte':
                    mapping = query_lte
                elif operator == 'gt':
                    mapping = query_gt
                elif operator == 'gte':
                    mapping = query_gte
                else:
                    raise TypeError(f'Unexpected operator {operator!r}. Must be one of {ALLOWED_OPERATORS}.')
            else:
                mapping = query_eq
                prefix = key

            if prefix not in ALLOWED_KEYS:
                raise TypeError(f'Unexpected argument {key!r}. Must be one of {ALLOWED_KEYS}.')

            mapping[prefix] = QueryEntry(value, prefix)

        self.query_eq = tuple(sorted(query_eq.items()))
        self.query_startswith = tuple(sorted(query_startswith.items()))
        self.query_endswith = tuple(sorted(query_endswith.items()))
        self.query_in = tuple(sorted(query_in.items()))
        self.query_contains = tuple(sorted(query_contains.items()))
        self.query_regex = tuple(sorted(query_regex.items()))
        self.query_lt = tuple(sorted(query_lt.items()))
        self.query_lte = tuple(sorted(query_lte.items()))
        self.query_gt = tuple(sorted(query_gt.items()))
        self.query_gte = tuple(sorted(query_gte.items()))

    def __str__(self):
        return 'Query(%s)' % (
            ', '.join([
                ', '.join(f'{key}{kind}={value!r}' for key, value in mapping)
                for kind, mapping in [
                    ('', self.query_eq),
                    ('_in', self.query_in),
                    ('_contains', self.query_contains),
                    ('_startswith', self.query_startswith),
                    ('_endswith', self.query_endswith),
                    ('_regex', self.query_regex),
                    ('_lt', self.query_lt),
                    ('_lte', self.query_lte),
                    ('_gt', self.query_gt),
                    ('_gte', self.query_gte),
                ]
                if mapping
            ])
        )

    def __repr__(self):
        return '<hunter.predicates.Query: %s>' % ' '.join([
            fmt % (mapping,)
            for fmt, mapping in [
                ('query_eq=%r', self.query_eq),
                ('query_in=%r', self.query_in),
                ('query_contains=%r', self.query_contains),
                ('query_startswith=%r', self.query_startswith),
                ('query_endswith=%r', self.query_endswith),
                ('query_regex=%r', self.query_regex),
                ('query_lt=%r', self.query_lt),
                ('query_lte=%r', self.query_lte),
                ('query_gt=%r', self.query_gt),
                ('query_gte=%r', self.query_gte),
            ]
            if mapping
        ])

    def __eq__(self, other):
        return (
            isinstance(other, Query)
            and self.query_eq == (<Query> other).query_eq
            and self.query_startswith == (<Query> other).query_startswith
            and self.query_endswith == (<Query> other).query_endswith
            and self.query_in == (<Query> other).query_in
            and self.query_contains == (<Query> other).query_contains
            and self.query_regex == (<Query> other).query_regex
            and self.query_lt == (<Query> other).query_lt
            and self.query_lte == (<Query> other).query_lte
            and self.query_gt == (<Query> other).query_gt
            and self.query_gte == (<Query> other).query_gte
        )

    def __call__(self, Event event):
        return fast_Query_call(self, event)

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)

cdef inline fast_Query_call(Query self, Event event):
    for key, entry in self.query_eq:
        value_from_event = (<QueryEntry> entry).getter(event)
        if value_from_event != (<QueryEntry> entry).value:
            return False
    for key, entry in self.query_in:
        value_from_event = (<QueryEntry> entry).getter(event)
        if (<str?>value_from_event) not in (<QueryEntry> entry).value:
            return False
    for key, entry in self.query_contains:
        value_from_event = (<QueryEntry> entry).getter(event)
        if (<QueryEntry> entry).value not in (<str?>value_from_event):
            return False
    for key, entry in self.query_startswith:
        value_from_event = (<QueryEntry> entry).getter(event)
        if not (<str?>value_from_event).startswith((<QueryEntry> entry).value):
            return False
    for key, entry in self.query_endswith:
        value_from_event = (<QueryEntry> entry).getter(event)
        if not (<str?>value_from_event).endswith((<QueryEntry> entry).value):
            return False
    for key, entry in self.query_regex:
        value_from_event = (<QueryEntry> entry).getter(event)
        if not (<QueryEntry> entry).value.match(value_from_event):
            return False
    for key, entry in self.query_gt:
        value_from_event = (<QueryEntry> entry).getter(event)
        if not value_from_event > (<QueryEntry> entry).value:
            return False
    for key, entry in self.query_gte:
        value_from_event = (<QueryEntry> entry).getter(event)
        if not value_from_event >= (<QueryEntry> entry).value:
            return False
    for key, entry in self.query_lt:
        value_from_event = (<QueryEntry> entry).getter(event)
        if not value_from_event < (<QueryEntry> entry).value:
            return False
    for key, entry in self.query_lte:
        value_from_event = (<QueryEntry> entry).getter(event)
        if not value_from_event <= (<QueryEntry> entry).value:
            return False

    return True


@cython.final
cdef class When:
    """
    Runs ``actions`` when ``condition(event)`` is ``True``.

    Actions take a single ``event`` argument.
    """

    def __init__(self, condition, *actions):
        if not actions:
            raise TypeError('Must give at least one action.')
        self.condition = condition
        self.actions = tuple(
            action() if isclass(action) and issubclass(action, Action) else action
            for action in actions)

    def __str__(self):
        return 'When(%s, %s)' % (
            self.condition,
            ', '.join(repr(p) for p in self.actions)
        )

    def __repr__(self):
        return '<hunter._predicates.When: condition=%r, actions=%r>' % (self.condition, self.actions)

    def __eq__(self, other):
        return (
            isinstance(other, When)
            and self.condition == (<When> other).condition
            and self.actions == (<When> other).actions
        )

    def __call__(self, Event event):
        return fast_When_call(self, event)

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)

cdef inline fast_When_call(When self, Event event):
    cdef object result

    result = fast_call(self.condition, event)

    if result:
        for action in self.actions:
            action(event)

    return result


@cython.final
cdef class From:
    """
    Keep running ``predicates`` after ``condition(event)`` is ``True``.
    """

    def __init__(self, condition, predicate=None, watermark=0):
        self.condition = condition
        self.predicate = predicate
        self.watermark = watermark
        self.origin_depth = -1
        self.origin_calls = -1

    def __str__(self):
        return 'From(%s, %s, watermark=%s)' % (
            self.condition, self.predicate, self.watermark
        )

    def __repr__(self):
        return '<hunter._predicates.From: condition=%r, predicate=%r, watermark=%r>' % (
            self.condition, self.predicate, self.watermark
        )

    def __eq__(self, other):
        return (
            isinstance(other, From)
            and self.condition == (<From> other).condition
            and self.predicate == (<From> other).predicate
        )

    def __call__(self, Event event):
        return fast_From_call(self, event)

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)

cdef inline fast_From_call(From self, Event event):
    cdef object result
    cdef int delta_depth
    cdef int delta_calls

    if self.origin_depth == -1:
        result = fast_call(self.condition, event)

        if result:
            self.origin_depth = event.depth
            self.origin_calls = event.calls
            delta_depth = delta_calls = 0
        else:
            return False
    else:
        delta_depth = event.depth - self.origin_depth
        delta_calls = event.calls - self.origin_calls
        if delta_depth < self.watermark:
            self.origin_depth = -1
            return False

    if self.predicate is None:
        return True
    else:
        relative_event = fast_clone(event)
        relative_event.depth = delta_depth
        relative_event.calls = delta_calls
        return fast_call(self.predicate, relative_event)


@cython.final
cdef class And:
    """
    `And` predicate. Exits at the first sub-predicate that returns ``False``.
    """
    def __init__(self, *predicates):
        self.predicates = predicates

    def __str__(self):
        return 'And(%s)' % ', '.join(str(p) for p in self.predicates)

    def __repr__(self):
        return '<hunter._predicates.And: predicates=%r>' % (self.predicates,)

    def __eq__(self, other):
        return (
            isinstance(other, And)
            and self.predicates == (<And> other).predicates
        )

    def __call__(self, Event event):
        return fast_And_call(self, event)

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        cdef list predicates
        if type(self) is And:
            predicates = list((<And> self).predicates)
        else:
            predicates = [self]
        if isinstance(other, And):
            predicates.extend((<And> other).predicates)
        else:
            predicates.append(other)
        return And(*predicates)

    def __invert__(self):
        return Not(self)

cdef inline fast_And_call(And self, Event event):
    for predicate in self.predicates:
        if not fast_call(predicate, event):
            return False
    else:
        return True


@cython.final
cdef class Or:
    """
    `Or` predicate. Exits at first sub-predicate that returns ``True``.
    """

    def __init__(self, *predicates):
        self.predicates = predicates

    def __str__(self):
        return 'Or(%s)' % ', '.join(str(p) for p in self.predicates)

    def __repr__(self):
        return '<hunter._predicates.Or: predicates=%r>' % (self.predicates,)

    def __eq__(self, other):
        return (
            isinstance(other, Or)
            and self.predicates == (<Or> other).predicates
        )

    def __call__(self, Event event):
        return fast_Or_call(self, event)

    def __or__(self, other):
        cdef list predicates
        if type(self) is Or:
            predicates = list((<Or> self).predicates)
        else:
            predicates = [self]
        if type(other) is Or:
            predicates.extend((<Or> other).predicates)
        else:
            predicates.append(other)
        return Or(*predicates)

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)

cdef inline fast_Or_call(Or self, Event event):
    for predicate in self.predicates:
        if fast_call(predicate, event):
            return True
    else:
        return False


cdef class Not:
    """
    `Not` predicate.
    """
    def __init__(self, predicate):
        self.predicate = predicate

    def __str__(self):
        return 'Not(%s)' % self.predicate

    def __repr__(self):
        return '<hunter._predicates.Not: predicate=%r>' % self.predicate

    def __eq__(self, other):
        return (
            isinstance(other, Not)
            and self.predicate == (<Not> other).predicate
        )

    def __call__(self, Event event):
        return fast_Not_call(self, event)

    def __or__(self, other):
        if type(self) is Not and type(other) is Not:
            return Not(And((<Not> self).predicate, (<Not> other).predicate))
        else:
            return Or(self, other)

    def __and__(self, other):
        if type(self) is Not and type(other) is Not:
            return Not(Or((<Not> self).predicate, (<Not> other).predicate))
        else:
            return And(self, other)

    def __invert__(self):
        return self.predicate

cdef inline fast_Not_call(Not self, Event event):
    return not fast_call(self.predicate, event)


cdef inline fast_call(callable, Event event):
    if type(callable) is Query:
        return fast_Query_call(<Query> callable, event)
    elif type(callable) is Or:
        return fast_Or_call(<Or> callable, event)
    elif type(callable) is And:
        return fast_And_call(<And> callable, event)
    elif type(callable) is Not:
        return fast_Not_call(<Not> callable, event)
    elif type(callable) is When:
        return fast_When_call(<When> callable, event)
    elif type(callable) is From:
        return fast_From_call(<From> callable, event)
    elif type(callable) is Backlog:
        return fast_Backlog_call(<Backlog> callable, event)
    else:
        return callable(event)


@cython.final
cdef class Backlog:
    def __init__(self, condition, size=100, stack=10, vars=False, strip=True, action=None, filter=None):
        self.action = action() if isclass(action) and issubclass(action, Action) else action
        if not isinstance(self.action, ColorStreamAction):
            raise TypeError("Action %r must be a ColorStreamAction." % self.action)
        self.condition = condition
        self.queue = deque(maxlen=size)
        self.size = size
        self.stack = stack
        self.strip = strip
        self.vars = vars
        self._try_repr = self.action.try_repr if self.vars else None
        self._filter = filter

    def __call__(self, event):
        return fast_Backlog_call(self, event)

    def __str__(self):
        return 'Backlog(%s, size=%s, stack=%s, vars=%s, action=%s, filter=%s)' % (
            self.condition, self.size, self.stack, self.vars, self.action, self._filter
        )

    def __repr__(self):
        return '<hunter.predicates.Backlog: condition=%r, size=%r, stack=%r, vars=%r, action=%r, filter=%r>' % (
            self.condition, self.size, self.stack, self.vars, self.action, self._filter
        )

    def __eq__(self, other):
        return (
            isinstance(other, Backlog) and
            self.condition == (<Backlog> other).condition and
            self.size == (<Backlog> other).size and
            self.stack == (<Backlog> other).stack and
            self.vars == (<Backlog> other).vars and
            self.action == (<Backlog> other).action
        )

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Backlog(Not(self.condition), size=self.size, stack=self.stack, vars=self.vars, action=self.action, filter=self._filter)

    def filter(self, *predicates, **kwargs):
        from hunter import _merge

        if self._filter is not None:
            predicates = (self._filter, *predicates)

        return Backlog(
            self.condition,
            size=self.size, stack=self.stack, vars=self.vars, action=self.action,
            filter=_merge(*predicates, **kwargs)
        )

cdef inline fast_Backlog_call(Backlog self, Event event):
    cdef bint first_is_call
    cdef Event detached_event
    cdef Event first_event
    cdef Event stack_event
    cdef FrameType first_frame
    cdef FrameType frame
    cdef int backlog_call_depth
    cdef int depth_delta
    cdef int first_depth
    cdef int missing_depth
    cdef object result
    cdef object stack_events

    result = fast_call(self.condition, event)
    if result:
        if self.queue:
            self.action.cleanup()

            first_event = <Event> self.queue[0]
            first_depth = first_event.depth
            backlog_call_depth = event.depth - first_depth
            first_is_call = first_event.kind == 'call'  # note that True is 1, thus the following math is valid
            missing_depth = min(first_depth,  max(0, self.stack - backlog_call_depth + first_is_call))
            if missing_depth:
                if first_is_call and first_event.frame is not None:
                    first_frame = first_event.frame.f_back
                else:
                    first_frame = first_event.frame
                if first_frame is not None:
                    stack_events = deque()  # a new deque because self.queue is limited, we can't add while it's full
                    frame = first_frame
                    depth_delta = 0
                    while frame and depth_delta < missing_depth:
                        stack_event = Event(
                            frame=frame, kind=0, arg=None,
                            threading_support=event.threading_support,
                            depth=first_depth - depth_delta - 1, calls=-1
                        )
                        if not self.vars:
                            # noinspection PyPropertyAccess
                            stack_event._locals = {}
                            stack_event._globals = {}
                            stack_event.detached = True
                        stack_events.appendleft(stack_event)
                        frame = frame.f_back
                        depth_delta += 1
                    for stack_event in stack_events:
                        if self._filter is None or self._filter(stack_event):
                            self.action(stack_event)
            for backlog_event in self.queue:
                if self._filter is None:
                    self.action(backlog_event)
                elif fast_call(self._filter, <Event> backlog_event):
                    self.action(backlog_event)
            self.queue.clear()
    else:
        if self.strip and event.depth < 1:
            # Looks like we're back to depth 0 for some reason.
            # Delete everything because we don't want to see what is likely just a long stream of useless returns.
            self.queue.clear()
        if self._filter is None or self._filter(event):
            detached_event = fast_detach(event, self._try_repr)
            detached_event.frame = event.frame
            self.queue.append(detached_event)

    return result

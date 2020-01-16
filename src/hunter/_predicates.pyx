# cython: linetrace=True, language_level=3str
from __future__ import absolute_import

import inspect
import re
from itertools import chain

cimport cython
from cpython.object cimport PyObject_RichCompare
from cpython.object cimport Py_EQ
from cpython.object cimport Py_NE

from ._event cimport Event

from .actions import Action

__all__ = (
    'And',
    'From',
    'Not',
    'Or',
    'Query',
    'When',
)

cdef tuple ALLOWED_KEYS = (
    'function', 'code', 'frame', 'module', 'lineno', 'globals', 'stdlib', 'arg', 'locals', 'kind', 'filename', 'source',
    'fullsource', 'threadname', 'threadid', 'depth', 'calls',
)
cdef tuple ALLOWED_OPERATORS = (
    'startswith', 'endswith', 'in', 'contains', 'regex',
    'sw', 'ew', 'has', 'rx',
    'gt', 'gte', 'lt', 'lte',
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
                raise TypeError('Unexpected argument %r. Must be one of %s with optional operators like: %s' % (
                    key, ALLOWED_KEYS, ALLOWED_OPERATORS
                ))
            elif count == 2:
                prefix, operator = parts
                if operator in ('startswith', 'sw'):
                    if not isinstance(value, basestring):
                        if not isinstance(value, (list, set, tuple)):
                            raise ValueError('Value %r for %r is invalid. Must be a string, list, tuple or set.' % (value, key))
                        value = tuple(value)
                    mapping = query_startswith
                elif operator in ('endswith', 'ew'):
                    if not isinstance(value, basestring):
                        if not isinstance(value, (list, set, tuple)):
                            raise ValueError('Value %r for %r is invalid. Must be a string, list, tuple or set.' % (value, key))
                        value = tuple(value)
                    mapping = query_endswith
                elif operator == 'in':
                    mapping = query_in
                elif operator in ('contains', 'has'):
                    mapping = query_contains
                elif operator in ('regex', 'rx'):
                    value = re.compile(value)
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
                    raise TypeError('Unexpected operator %r. Must be one of %s.' % (operator, ALLOWED_OPERATORS))
            else:
                mapping = query_eq
                prefix = key

            if prefix not in ALLOWED_KEYS:
                raise TypeError('Unexpected argument %r. Must be one of %s.' % (key, ALLOWED_KEYS))

            mapping[prefix] = value

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
            ', '.join(
                ', '.join('%s%s=%r' % (key, kind, value) for key, value in mapping)
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
                ] if mapping
            )
        )

    def __repr__(self):
        return '<hunter._predicates.Query: %s>' % ' '.join(
            fmt % (mapping,) for fmt, mapping in [
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

            ] if mapping
        )

    def __eq__(self, other):
        return (
            isinstance(other, Query)
            and self.query_eq == (<Query> other).query_eq
            and self.query_startswith == (<Query> other).query_startswith
            and self.query_endswith == (<Query> other).query_endswith
            and self.query_in == (<Query> other).query_in
            and self.query_contains == (<Query> other).query_contains
            and self.query_regex == (<Query> other).query_regex
            and self.query_lt == (<Query>other).query_lt
            and self.query_lte == (<Query>other).query_lte
            and self.query_gt == (<Query>other).query_gt
            and self.query_gte == (<Query>other).query_gte
        )

    def __hash__(self):
        return hash((
            'Query',
            self.query_eq,
            self.query_in,
            self.query_contains,
            self.query_startswith,
            self.query_endswith,
            self.query_regex,
            self.query_lt,
            self.query_lte,
            self.query_gt,
            self.query_gte,
        ))

    def __call__(self, Event event):
        return fast_Query_call(self, event)

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)

cdef fast_Query_call(Query self, Event event):
    for key, value in self.query_eq:
        evalue = event[key]
        if evalue != value:
            return False
    for key, value in self.query_in:
        evalue = event[key]
        if evalue not in value:
            return False
    for key, value in self.query_contains:
        evalue = event[key]
        if value not in evalue:
            return False
    for key, value in self.query_startswith:
        evalue = event[key]
        if not evalue.startswith(value):
            return False
    for key, value in self.query_endswith:
        evalue = event[key]
        if not evalue.endswith(value):
            return False
    for key, value in self.query_regex:
        evalue = event[key]
        if not value.match(evalue):
            return False
    for key, value in self.query_gt:
        evalue = event[key]
        if not evalue > value:
            return False
    for key, value in self.query_gte:
        evalue = event[key]
        if not evalue >= value:
            return False
    for key, value in self.query_lt:
        evalue = event[key]
        if not evalue < value:
            return False
    for key, value in self.query_lte:
        evalue = event[key]
        if not evalue <= value:
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
            action() if inspect.isclass(action) and issubclass(action, Action) else action
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

    def __hash__(self):
        return hash(('When', self.condition, self.actions))

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

    def __hash__(self):
        return hash(('From', self.condition, self.predicate))

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
        relative_event = event.clone()
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

    def __hash__(self):
        return hash(('And', self.predicates))

    def __call__(self, Event event):
        return fast_And_call(self, event)

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        cdef list predicates
        if type(self) is And:
            predicates = list((<And>self).predicates)
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

    def __hash__(self):
        return hash(('Or', self.predicates))

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

    def __hash__(self):
        return hash(('Not', self.predicate))

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
    else:
        return callable(event)

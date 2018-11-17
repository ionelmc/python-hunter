from __future__ import absolute_import

import inspect
import re
from itertools import chain

from six import string_types

from .actions import Action
from .event import Event

ALLOWED_KEYS = tuple(i for i in Event.__dict__.keys() if not i.startswith('_') and i not in ('tracer', 'thread'))
ALLOWED_OPERATORS = (
    'startswith', 'endswith', 'in', 'contains', 'regex',
    'sw', 'ew', 'has', 'rx',
    'gt', 'gte', 'lt', 'lte',
)


def _sloppy_hash(obj):
    try:
        return hash(obj)
    except TypeError:
        return 'id(%x)' % id(obj)


class Query(object):
    """
    A query class.

    See :class:`hunter.Event` for fields that can be filtered on.
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
                    if not isinstance(value, string_types):
                        if not isinstance(value, (list, set, tuple)):
                            raise ValueError('Value %r for %r is invalid. Must be a string, list, tuple or set.' % (value, key))
                        value = tuple(value)
                    mapping = query_startswith
                elif operator in ('endswith', 'ew'):
                    if not isinstance(value, string_types):
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
        return '<hunter.predicates.Query: %s>' % ' '.join(
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
            and self.query_eq == other.query_eq
            and self.query_in == other.query_in
            and self.query_contains == other.query_contains
            and self.query_startswith == other.query_startswith
            and self.query_endswith == other.query_endswith
            and self.query_regex == other.query_regex
            and self.query_lt == other.query_lt
            and self.query_lte == other.query_lte
            and self.query_gt == other.query_gt
            and self.query_gte == other.query_gte
        )

    def __call__(self, event):
        """
        Handles event. Returns True if all criteria matched.
        """
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

    def __invert__(self):
        return Not(self)

    __ror__ = __or__
    __rand__ = __and__


class When(object):
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
        return '<hunter.predicates.When: condition=%r, actions=%r>' % (self.condition, self.actions)

    def __eq__(self, other):
        return (
            isinstance(other, When)
            and self.condition == other.condition
            and self.actions == other.actions
        )

    def __call__(self, event):
        """
        Handles the event.
        """
        if self.condition(event):
            for action in self.actions:
                action(event)
            return True
        else:
            return False

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)

    __ror__ = __or__
    __rand__ = __and__


class And(object):
    """
    `And` predicate. Exits at the first sub-predicate that returns ``False``.
    """

    def __init__(self, *predicates):
        self.predicates = predicates

    def __str__(self):
        return 'And(%s)' % ', '.join(str(p) for p in self.predicates)

    def __repr__(self):
        return '<hunter.predicates.And: predicates=%r>' % (self.predicates,)

    def __call__(self, event):
        """
        Handles the event.
        """
        for predicate in self.predicates:
            if not predicate(event):
                return False
        else:
            return True

    def __eq__(self, other):
        return (
            isinstance(other, And)
            and self.predicates == other.predicates
        )

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(*chain(self.predicates, other.predicates if isinstance(other, And) else (other,)))

    def __invert__(self):
        return Not(self)

    def __hash__(self):
        return hash(frozenset(self.predicates))

    __ror__ = __or__
    __rand__ = __and__


class Or(object):
    """
    `Or` predicate. Exits at first sub-predicate that returns ``True``.
    """

    def __init__(self, *predicates):
        self.predicates = predicates

    def __str__(self):
        return 'Or(%s)' % ', '.join(str(p) for p in self.predicates)

    def __repr__(self):
        return '<hunter.predicates.Or: predicates=%r>' % (self.predicates,)

    def __call__(self, event):
        """
        Handles the event.
        """
        for predicate in self.predicates:
            if predicate(event):
                return True
        else:
            return False

    def __eq__(self, other):
        return (
            isinstance(other, Or)
            and self.predicates == other.predicates
        )

    def __or__(self, other):
        return Or(*chain(self.predicates, other.predicates if isinstance(other, Or) else (other,)))

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)

    def __hash__(self):
        return hash(frozenset(self.predicates))

    __ror__ = __or__
    __rand__ = __and__


class Not(object):
    """
    `Not` predicate.
    """
    def __init__(self, predicate):
        self.predicate = predicate

    def __str__(self):
        return 'Not(%s)' % self.predicate

    def __repr__(self):
        return '<hunter.predicates.Not: predicate=%r>' % self.predicate

    def __eq__(self, other):
        return (
            isinstance(other, Not)
            and self.predicate == other.predicate
        )

    def __call__(self, event):
        """
        Handles the event.
        """
        return not self.predicate(event)

    def __or__(self, other):
        if isinstance(other, Not):
            return Not(And(self.predicate, other.predicate))
        else:
            return Or(self, other)

    def __and__(self, other):
        if isinstance(other, Not):
            return Not(Or(self.predicate, other.predicate))
        else:
            return And(self, other)

    def __invert__(self):
        return self.predicate

    __ror__ = __or__
    __rand__ = __and__

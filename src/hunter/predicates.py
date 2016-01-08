from __future__ import absolute_import

import inspect
import re
from itertools import chain

from fields import Fields
from six import string_types

from .actions import Action
from .event import Event

ALLOWED_KEYS = tuple(i for i in Event.__dict__.keys() if not i.startswith('_') and i != 'tracer')
ALLOWED_OPERATORS = 'startswith', 'endswith', 'in', 'contains', 'regex'


def _sloppy_hash(obj):
    try:
        return hash(obj)
    except TypeError:
        return 'id(%x)' % id(obj)


class Query(Fields.query_eq.query_startswith.query_endswith.query_in.query_contains):
    """
    A query class.

    See :class:`hunter.Event` for fields that can be filtered on.
    """
    def __init__(self, **query):
        """
        Args:
            query: criteria to match on.

                Accepted arguments: ``arg``, ``code``, ``filename``, ``frame``, ``fullsource``, ``function``,
                ``globals``, ``kind``, ``lineno``, ``locals``, ``module``, ``source``, ``stdlib``, ``tracer``.
        """
        query_eq = {}
        query_startswith = {}
        query_endswith = {}
        query_in = {}
        query_contains = {}
        query_regex = {}

        for key, value in query.items():
            parts = [p for p in key.split('_') if p]
            count = len(parts)
            if count > 2:
                raise TypeError('Unexpected argument %r. Must be one of %s with optional operators like: %s' % (
                    key, ALLOWED_KEYS, ALLOWED_OPERATORS
                ))
            elif count == 2:
                prefix, operator = parts
                if operator == 'startswith':
                    if not isinstance(value, string_types):
                        if not isinstance(value, (list, set, tuple)):
                            raise ValueError('Value %r for %r is invalid. Must be a string, list, tuple or set.' % (value, key))
                        value = tuple(value)
                    mapping = query_startswith
                elif operator == 'endswith':
                    if not isinstance(value, string_types):
                        if not isinstance(value, (list, set, tuple)):
                            raise ValueError('Value %r for %r is invalid. Must be a string, list, tuple or set.' % (value, key))
                        value = tuple(value)
                    mapping = query_endswith
                elif operator == 'in':
                    mapping = query_in
                elif operator == 'contains':
                    mapping = query_contains
                elif operator == 'regex':
                    value = re.compile(value)
                    mapping = query_regex
                else:
                    raise TypeError('Unexpected operator %r. Must be one of %s.'.format(operator, ALLOWED_OPERATORS))
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
            ] if mapping
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


class When(Fields.condition.actions):
    """
    Runs ``actions`` when ``condition(event)`` is ``True``.

    Actions take a single ``event`` argument.
    """

    def __init__(self, condition, *actions):
        if not actions:
            raise TypeError('Must give at least one action.')
        super(When, self).__init__(condition, tuple(
            action() if inspect.isclass(action) and issubclass(action, Action) else action
            for action in actions))

    def __str__(self):
        return 'When(%s, %s)' % (
            self.condition,
            ', '.join(repr(p) for p in self.actions)
        )

    def __repr__(self):
        return '<hunter.predicates.When: condition=%r, actions=%r>' % (self.condition, self.actions)

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


class And(Fields.predicates):
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
        if isinstance(other, And):
            if len(self.predicates) != len(other.predicates):
                return False
            return set(self.predicates) == set(other.predicates)
        return NotImplemented

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(*chain(self.predicates, other.predicates if isinstance(other, And) else (other,)))

    def __invert__(self):
        return Not(self)

    def __hash__(self):
        return hash(frozenset(self.predicates))


class Or(Fields.predicates):
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
        if isinstance(other, Or):
            if len(self.predicates) != len(other.predicates):
                return False
            return set(self.predicates) == set(other.predicates)
        return NotImplemented

    def __or__(self, other):
        return Or(*chain(self.predicates, other.predicates if isinstance(other, Or) else (other,)))

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)

    def __hash__(self):
        return hash(frozenset(self.predicates))


class Not(Fields.predicate):
    """
    `Not` predicate.
    """

    def __str__(self):
        return 'Not(%s)' % self.predicate

    def __repr__(self):
        return '<hunter.predicates.Not: predicate=%r>' % self.predicate

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

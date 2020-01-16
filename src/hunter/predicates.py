from __future__ import absolute_import

import inspect
import re
from itertools import chain

from .actions import Action
from .event import Event
from .util import StringType

__all__ = (
    'And',
    'From',
    'Not',
    'Or',
    'Query',
    'When',
)

ALLOWED_KEYS = tuple(sorted(
    i for i in Event.__dict__.keys()
    if not i.startswith('_') and i not in ('tracer', 'thread', 'frame')
))
ALLOWED_OPERATORS = (
    'startswith', 'endswith', 'in', 'contains', 'regex',
    'sw', 'ew', 'has', 'rx',
    'gt', 'gte', 'lt', 'lte',
)


class Query(object):
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
                    if not isinstance(value, StringType):
                        if not isinstance(value, (list, set, tuple)):
                            raise ValueError('Value %r for %r is invalid. Must be a string, list, tuple or set.' % (value, key))
                        value = tuple(value)
                    mapping = query_startswith
                elif operator in ('endswith', 'ew'):
                    if not isinstance(value, StringType):
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
        Convenience API so you can do ``Query(...) | Query(...)``. It converts that to ``Or(Query(...), Query(...))``.
        """
        return Or(self, other)

    def __and__(self, other):
        """
        Convenience API so you can do ``Query(...) & Query(...)``. It converts that to ``And(Query(...), Query(...))``.
        """
        return And(self, other)

    def __invert__(self):
        """
        Convenience API so you can do ``~Query(...)``. It converts that to ``Not(Query(...))``.
        """
        return Not(self)

    def __ror__(self, other):
        """
        Convenience API so you can do ``other | Query(...)``. It converts that to ``Or(other, Query(...))``.
        """
        return Or(other, self)

    def __rand__(self, other):
        """
        Convenience API so you can do ``other & Query(...)``. It converts that to ``And(other, Query(...))``.
        """
        return And(other, self)


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

    def __hash__(self):
        return hash(('When', self.condition, self.actions))

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
        """
        Convenience API so you can do ``When(...) | other``. It converts that to ``Or(When(...), other)``.
        """
        return Or(self, other)

    def __and__(self, other):
        """
        Convenience API so you can do ``When(...) & other``. It converts that to ``And(When(...), other)``.
        """
        return And(self, other)

    def __invert__(self):
        """
        Convenience API so you can do ``~When(...)``. It converts that to ``Not(When(...))``.
        """
        return Not(self)

    def __ror__(self, other):
        """
        Convenience API so you can do ``other | When(...)``. It converts that to ``Or(other, When(...))``.
        """
        return Or(other, self)

    def __rand__(self, other):
        """
        Convenience API so you can do ``other & When(...)``. It converts that to ``And(other, When(...))``.
        """
        return And(other, self)


class From(object):
    """
    From-point filtering mechanism. Switches on to running the predicate after condition matches, and switches off when
    the depth goes lower than the initial level.

    After ``condition(event)`` returns ``True`` the ``event.depth`` will be saved and calling this object with an
    ``event`` will return ``predicate(event)`` until ``event.depth - watermark`` is equal to the depth that was saved.

    Args:
        condition (callable): A callable that returns True/False or a :class:`~hunter.predicates.Query` object.
        predicate (callable): Optional callable that returns True/False or a :class:`~hunter.predicates.Query` object to
            run after ``condition`` first returns ``True``. Note that this predicate will be called with a event-copy that has adjusted
            :attr:`~hunter.event.Event.depth` and :attr:`~hunter.event.Event.calls` to the initial point where the ``condition`` matched.
            In other words they will be relative.
        watermark (int): Depth difference to switch off and wait again on ``condition``.
    """

    def __init__(self, condition, predicate=None, watermark=0):
        self.condition = condition
        self.predicate = predicate
        self.watermark = watermark
        self.origin_depth = None
        self.origin_calls = None

    def __str__(self):
        return 'From(%s, %s, watermark=%s)' % (
            self.condition, self.predicate, self.watermark
        )

    def __repr__(self):
        return '<hunter.predicates.From: condition=%r, predicate=%r, watermark=%r>' % (
            self.condition, self.predicate, self.watermark
        )

    def __eq__(self, other):
        return (
            isinstance(other, From)
            and self.condition == other.condition
            and self.predicate == other.predicate
        )

    def __hash__(self):
        return hash(('From', self.condition, self.predicate))

    def __call__(self, event):
        """
        Handles the event.
        """
        if self.origin_depth is None:
            if self.condition(event):
                self.origin_depth = event.depth
                self.origin_calls = event.calls
                delta_depth = delta_calls = 0
            else:
                return False
        else:
            delta_depth = event.depth - self.origin_depth
            delta_calls = event.calls - self.origin_calls
            if delta_depth < self.watermark:
                self.origin_depth = None
                return False
        if self.predicate is None:
            return True
        else:
            relative_event = event.clone()
            relative_event.depth = delta_depth
            relative_event.calls = delta_calls
            return self.predicate(relative_event)

    def __or__(self, other):
        """
        Convenience API so you can do ``From(...) | other``. It converts that to ``Or(From(...), other)``.
        """
        return Or(self, other)

    def __and__(self, other):
        """
        Convenience API so you can do ``From(...) & other``. It converts that to ``And(From(...), other))``.
        """
        return And(self, other)

    def __invert__(self):
        """
        Convenience API so you can do ``~From(...)``. It converts that to ``Not(From(...))``.
        """
        return Not(self)

    def __ror__(self, other):
        """
        Convenience API so you can do ``other | From(...)``. It converts that to ``Or(other, From(...))``.
        """
        return Or(other, self)

    def __rand__(self, other):
        """
        Convenience API so you can do ``other & From(...)``. It converts that to ``And(other, From(...))``.
        """
        return And(other, self)


class And(object):
    """
    Returns ``False`` at the first sub-predicate that returns ``False``, otherwise returns ``True``.
    """

    def __init__(self, *predicates):
        self.predicates = predicates

    def __str__(self):
        return 'And(%s)' % ', '.join(str(p) for p in self.predicates)

    def __repr__(self):
        return '<hunter.predicates.And: predicates=%r>' % (self.predicates,)

    def __eq__(self, other):
        return (
            isinstance(other, And)
            and self.predicates == other.predicates
        )

    def __hash__(self):
        return hash(('And', self.predicates))

    def __call__(self, event):
        """
        Handles the event.
        """
        for predicate in self.predicates:
            if not predicate(event):
                return False
        else:
            return True

    def __or__(self, other):
        """
        Convenience API so you can do ``And(...) | other``. It converts that to ``Or(And(...), other)``.
        """
        return Or(self, other)

    def __and__(self, other):
        """
        Convenience API so you can do ``And(...) & other``. It converts that to ``And(..., other)``.
        """
        return And(*chain(self.predicates, other.predicates if isinstance(other, And) else (other,)))

    def __invert__(self):
        """
        Convenience API so you can do ``~And(...)``. It converts that to ``Not(And(...))``.
        """
        return Not(self)

    def __ror__(self, other):
        """
        Convenience API so you can do ``other | And(...)``. It converts that to ``Or(other, And(...))``.
        """
        return Or(other, self)

    def __rand__(self, other):
        """
        Convenience API so you can do ``other & And(...)``. It converts that to ``And(other, And(...))``.
        """
        return And(other, *self.predicates)


class Or(object):
    """
    Returns ``True`` after the first sub-predicate that returns ``True``.
    """

    def __init__(self, *predicates):
        self.predicates = predicates

    def __str__(self):
        return 'Or(%s)' % ', '.join(str(p) for p in self.predicates)

    def __repr__(self):
        return '<hunter.predicates.Or: predicates=%r>' % (self.predicates,)

    def __eq__(self, other):
        return (
            isinstance(other, Or)
            and self.predicates == other.predicates
        )

    def __hash__(self):
        return hash(('Or', self.predicates))

    def __call__(self, event):
        """
        Handles the event.
        """
        for predicate in self.predicates:
            if predicate(event):
                return True
        else:
            return False

    def __or__(self, other):
        """
        Convenience API so you can do ``Or(...) | other``. It converts that to ``Or(..., other)``.
        """
        return Or(*chain(self.predicates, other.predicates if isinstance(other, Or) else (other,)))

    def __and__(self, other):
        """
        Convenience API so you can do ``Or(...) & other``. It converts that to ``And(Or(...), other)``.
        """
        return And(self, other)

    def __invert__(self):
        """
        Convenience API so you can do ``~Or(...)``. It converts that to ``Not(Or(...))``.
        """
        return Not(self)

    def __ror__(self, other):
        """
        Convenience API so you can do ``other | Or(...)``. It converts that to ``Or(other, Or(...))``.
        """
        return Or(other, *self.predicates)

    def __rand__(self, other):
        """
        Convenience API so you can do ``other & Or(...)``. It converts that to ``And(other, Or(...))``.
        """
        return And(other, self)


class Not(object):
    """
    Simply returns ``not predicate(event)``.
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

    def __hash__(self):
        return hash(('Not', self.predicate))

    def __call__(self, event):
        """
        Handles the event.
        """
        return not self.predicate(event)

    def __or__(self, other):
        """
        Convenience API so you can do ``Not(...) | other``. It converts that to ``Or(Not(...), other)``.

        Note that ``Not(...) | Not(...)`` converts to ``Not(And(..., ...))``.
        """
        if isinstance(other, Not):
            return Not(And(self.predicate, other.predicate))
        else:
            return Or(self, other)

    def __and__(self, other):
        """
        Convenience API so you can do ``Not(...) & other``. It converts that to ``And(Not(...), other)``.

        Note that ``Not(...) & Not(...)`` converts to ``Not(Or(..., ...))``.
        """
        if isinstance(other, Not):
            return Not(Or(self.predicate, other.predicate))
        else:
            return And(self, other)

    def __invert__(self):
        """
        Convenience API so you can do ``~Not(...)``. It converts that to ``...``.
        """
        return self.predicate

    def __ror__(self, other):
        """
        Convenience API so you can do ``other | Not(...)``. It converts that to ``Or(other, Not(...))``.
        """
        return Or(other, self)

    def __rand__(self, other):
        """
        Convenience API so you can do ``other & Not(...)``. It converts that to ``And(other, Not(...))``.
        """
        return And(other, self)

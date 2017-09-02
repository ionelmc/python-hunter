# cython: linetrace=True
from __future__ import absolute_import

import inspect
import re
from itertools import chain

cimport cython
from cpython.object cimport PyObject_RichCompare, Py_EQ, Py_NE

from .actions import Action

cdef tuple ALLOWED_KEYS = (
    'function', 'code', 'frame', 'module', 'lineno', 'globals', 'stdlib', 'arg', 'locals', 'kind', 'filename', 'source',
    'fullsource', 'tracer', 'threadname', 'threadid', 'depth', 'calls',
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

    def __call__(self, event):
        """
        Handles event. Returns True if all criteria matched.
        """
        return fast_Query_call(self, event)

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

    def __ror__(self, other):
        """
        Convenience API so you can do ``Q() | Q()``. It converts that to ``Or(Q(), Q())``.
        """
        return Or(self, other)

    def __rand__(self, other):
        """
        Convenience API so you can do ``Q() & Q()``. It converts that to ``And(Q(), Q())``.
        """
        return And(self, other)

    def __invert__(self):
        return Not(self)

    def __richcmp__(self, other, int op):
        is_equal = (
            isinstance(other, Query)
            and self.query_eq == (<Query> other).query_eq
            and self.query_startswith == (<Query> other).query_startswith
            and self.query_endswith == (<Query> other).query_endswith
            and self.query_in == (<Query> other).query_in
            and self.query_contains == (<Query> other).query_contains
            and self.query_regex == (<Query> other).query_regex
        )

        if op == Py_EQ:
            return is_equal
        elif op == Py_NE:
            return not is_equal
        else:
            return PyObject_RichCompare(id(self), id(other), op)

    def __hash__(self):
        return hash((
            self.query_eq,
            self.query_startswith,
            self.query_endswith,
            self.query_in,
            self.query_contains,
            self.query_regex
        ))

cdef fast_Query_call(Query self, event):
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
            raise TypeError("Must give at least one action.")
        self.condition = condition
        self.actions = tuple(
            action() if inspect.isclass(action) and issubclass(action, Action) else action
            for action in actions)

    def __str__(self):
        return "When(%s, %s)" % (
            self.condition,
            ', '.join(repr(p) for p in self.actions)
        )

    def __repr__(self):
        return "<hunter._predicates.When: condition=%r, actions=%r>" % (self.condition, self.actions)

    def __call__(self, event):
        """
        Handles the event.
        """
        return fast_When_call(self, event)

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __ror__(self, other):
        return Or(self, other)

    def __rand__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)

    def __richcmp__(self, other, int op):
        is_equal = (
            isinstance(other, When) and
            self.condition == (<When> other).condition and
            self.actions == (<When> other).actions
        )

        if op == Py_EQ:
            return is_equal
        elif op == Py_NE:
            return not is_equal
        else:
            return PyObject_RichCompare(id(self), id(other), op)

    def __hash__(self):
        return hash((self.condition, self.actions))

cdef inline fast_When_call(When self, event):
    cdef object result
    condition = self.condition

    if type(condition) is Query:
        result = fast_Query_call(<Query> condition, event)
    elif type(condition) is Or:
        result = fast_Or_call(<Or> condition, event)
    elif type(condition) is And:
        result = fast_And_call(<And> condition, event)
    elif type(condition) is Not:
        result = fast_Not_call(<Not> condition, event)
    elif type(condition) is When:
        result = fast_When_call(<When> condition, event)
    else:
        result = condition(event)

    if result:
        for action in self.actions:
            action(event)

    return result


@cython.final
cdef class And:
    """
    `And` predicate. Exits at the first sub-predicate that returns ``False``.
    """
    def __init__(self, *predicates):
        self.predicates = predicates

    def __str__(self):
        return "And(%s)" % ', '.join(str(p) for p in self.predicates)

    def __repr__(self):
        return "<hunter._predicates.And: predicates=%r>" % (self.predicates,)

    def __call__(self, event):
        """
        Handles the event.
        """
        return fast_And_call(self, event)

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(*chain(self.predicates, other.predicates if isinstance(other, And) else (other,)))

    def __ror__(self, other):
        return Or(self, other)

    def __rand__(self, other):
        return And(*chain(self.predicates, other.predicates if isinstance(other, And) else (other,)))

    def __invert__(self):
        return Not(self)

    def __richcmp__(self, other, int op):
        is_equal = isinstance(other, And) and set(self.predicates) == set((<And> other).predicates)

        if op == Py_EQ:
            return is_equal
        elif op == Py_NE:
            return not is_equal
        else:
            return PyObject_RichCompare(id(self), id(other), op)

    def __hash__(self):
        return hash(frozenset(self.predicates))

cdef inline fast_And_call(And self, event):
    for predicate in self.predicates:
        if type(predicate) is Query:
            if not fast_Query_call(<Query> predicate, event):
                return False
        elif type(predicate) is Or:
            if not fast_Or_call(<Or> predicate, event):
                return False
        elif type(predicate) is And:
            if not fast_And_call(<And> predicate, event):
                return False
        elif type(predicate) is Not:
            if not fast_Not_call(<Not> predicate, event):
                return False
        elif type(predicate) is When:
            if not fast_When_call(<When> predicate, event):
                return False
        else:
            if not predicate(event):
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
        return "Or(%s)" % ', '.join(str(p) for p in self.predicates)

    def __repr__(self):
        return "<hunter._predicates.Or: predicates=%r>" % (self.predicates,)

    def __call__(self, event):
        """
        Handles the event.
        """
        return fast_Or_call(self, event)

    def __or__(self, other):
        return Or(*chain(self.predicates, other.predicates if isinstance(other, Or) else (other,)))

    def __and__(self, other):
        return And(self, other)

    def __ror__(self, other):
        return Or(*chain(self.predicates, other.predicates if isinstance(other, Or) else (other,)))

    def __rand__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)

    def __richcmp__(self, other, int op):
        is_equal = isinstance(other, Or) and set(self.predicates) == set((<Or> other).predicates)

        if op == Py_EQ:
            return is_equal
        elif op == Py_NE:
            return not is_equal
        else:
            return PyObject_RichCompare(id(self), id(other), op)

    def __hash__(self):
        return hash(frozenset(self.predicates))

cdef inline fast_Or_call(Or self, event):
    for predicate in self.predicates:
        if type(predicate) is Query:
            if fast_Query_call(<Query> predicate, event):
                return True
        elif type(predicate) is Or:
            if fast_Or_call(<Or> predicate, event):
                return True
        elif type(predicate) is And:
            if fast_And_call(<And> predicate, event):
                return True
        elif type(predicate) is Not:
            if fast_Not_call(<Not> predicate, event):
                return True
        elif type(predicate) is When:
            if fast_When_call(<When> predicate, event):
                return True
        else:
            if predicate(event):
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
        return "Not(%s)" % self.predicate

    def __repr__(self):
        return "<hunter._predicates.Not: predicate=%r>" % self.predicate

    def __call__(self, event):
        """
        Handles the event.
        """
        return fast_Not_call(self, event)

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

    def __ror__(self, other):
        if isinstance(other, Not):
            return Not(And(self.predicate, other.predicate))
        else:
            return Or(self, other)

    def __rand__(self, other):
        if isinstance(other, Not):
            return Not(Or(self.predicate, other.predicate))
        else:
            return And(self, other)

    def __invert__(self):
        return self.predicate

    def __richcmp__(self, other, int op):
        is_equal = isinstance(other, Not) and self.predicate == (<Not> other).predicate

        if op == Py_EQ:
            return is_equal
        elif op == Py_NE:
            return not is_equal
        else:
            return PyObject_RichCompare(id(self), id(other), op)

    def __hash__(self):
        return hash(self.predicate)

cdef inline fast_Not_call(Not self, event):
    predicate = self.predicate

    if type(predicate) is Query:
        return not fast_Query_call(<Query> predicate, event)
    elif type(predicate) is Or:
        return not fast_Or_call(<Or> predicate, event)
    elif type(predicate) is And:
        return not fast_And_call(<And> predicate, event)
    elif type(predicate) is Not:
        return not fast_Not_call(<Not> predicate, event)
    elif type(predicate) is When:
        return not fast_When_call(<When> predicate, event)
    else:
        return not predicate(event)

from __future__ import absolute_import

cimport cython

import inspect
from itertools import chain
from cpython.object cimport PyObject_RichCompare, Py_EQ, Py_NE

from six import string_types

from .actions import Action

cdef tuple ALLOWED = (
    'function', 'code', 'frame', 'module', 'lineno', 'globals', 'stdlib', 'arg', 'locals', 'kind', 'filename', 'source',
    'fullsource', 'tracer'
)

@cython.final
cdef class Query:
    """
    A query class.

    See :class:`hunter.Event` for fields that can be filtered on.
    """
    cdef readonly dict query

    def __init__(self, **query):
        """
        Args:
            query: criteria to match on.

                Accepted arguments: ``arg``, ``code``, ``filename``, ``frame``, ``fullsource``, ``function``,
                ``globals``, ``kind``, ``lineno``, ``locals``, ``module``, ``source``, ``stdlib``, ``tracer``.
        """
        for key in query:
            if key not in ALLOWED:
                raise TypeError("Unexpected argument {!r}. Must be one of {}.".format(key, ALLOWED))
        self.query = query

    def __str__(self):
        return "Query(%s)" % (
            ', '.join("%s=%r" % item for item in self.query.items()),
        )

    def __repr__(self):
        return "<hunter._predicates.Query: query=%r>" % self.query

    def __call__(self, event):
        """
        Handles event. Returns True if all criteria matched.
        """
        for key, value in self.query.items():
            evalue = event[key]
            if isinstance(evalue, string_types) and isinstance(value, (list, tuple, set)):
                if not evalue.startswith(tuple(value)):
                    return False
            elif evalue != value:
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

    def __richcmp__(self, other, int op):
        is_equal = isinstance(other, Query) and self.query == (<Query> other).query

        if op == Py_EQ:
            return is_equal
        if op == Py_NE:
            return not is_equal
        return PyObject_RichCompare(id(self), id(other), op)

@cython.final
cdef class When:
    """
    Runs ``actions`` when ``condition(event)`` is ``True``.

    Actions take a single ``event`` argument.
    """
    cdef:
        readonly object condition
        readonly list actions

    def __init__(self, condition, *actions):
        if not actions:
            raise TypeError("Must give at least one action.")
        self.condition = condition
        self.actions = [
            action() if inspect.isclass(action) and issubclass(action, Action) else action
            for action in actions]

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
        if self.condition(event):
            for action in self.actions:
                action(event)

            return True

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __richcmp__(self, other, int op):
        is_equal = (
            isinstance(other, When) and
            self.condition == (<When> other).condition and
            self.actions == (<When> other).actions
        )

        if op == Py_EQ:
            return is_equal
        if op == Py_NE:
            return not is_equal
        return PyObject_RichCompare(id(self), id(other), op)


@cython.final
cdef class And:
    """
    `And` predicate. Exits at the first sub-predicate that returns ``False``.
    """
    cdef readonly tuple predicates

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
        for predicate in self.predicates:
            if not predicate(event):
                return False
        return True

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(*chain(self.predicates, other.predicates if isinstance(other, And) else (other,)))

    def __invert__(self):
        return Not(self)

    def __richcmp__(self, other, int op):
        is_equal = isinstance(other, And) and self.predicates == (<And> other).predicates

        if op == Py_EQ:
            return is_equal
        if op == Py_NE:
            return not is_equal
        return PyObject_RichCompare(id(self), id(other), op)

@cython.final
cdef class Or:
    """
    `Or` predicate. Exits at first sub-predicate that returns ``True``.
    """
    cdef readonly tuple predicates

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
        for predicate in self.predicates:
            if predicate(event):
                return True
        return False

    def __or__(self, other):
        return Or(*chain(self.predicates, other.predicates if isinstance(other, Or) else (other,)))

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)

    def __richcmp__(self, other, int op):
        is_equal = isinstance(other, Or) and self.predicates == (<Or> other).predicates

        if op == Py_EQ:
            return is_equal
        if op == Py_NE:
            return not is_equal
        return PyObject_RichCompare(id(self), id(other), op)

cdef class Not:
    """
    `Not` predicate.
    """
    cdef readonly object predicate

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
        return not self.predicate(event)

    def __or__(self, other):
        if isinstance(other, Not):
            return Not(And(self.predicate, other.predicate))
        return Or(self, other)

    def __and__(self, other):
        if isinstance(other, Not):
            return Not(Or(self.predicate, other.predicate))
        return And(self, other)

    def __invert__(self):
        return self.predicate

    def __richcmp__(self, other, int op):
        is_equal = isinstance(other, Not) and self.predicate == (<Not> other).predicate

        if op == Py_EQ:
            return is_equal
        if op == Py_NE:
            return not is_equal
        return PyObject_RichCompare(id(self), id(other), op)

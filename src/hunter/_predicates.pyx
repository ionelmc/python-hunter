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
    cdef:
        dict query


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

    def __repr__(self):
        return "Query({})".format(
            ', '.join("{}={!r}".format(*item) for item in self.query.items()),
        )

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

@cython.final
cdef class When:
    """
    Runs ``actions`` when ``condition(event)`` is ``True``.

    Actions take a single ``event`` argument.
    """
    cdef:
        object condition
        list actions

    def __init__(self, condition, *actions):
        if not actions:
            raise TypeError("Must give at least one action.")
        self.condition = condition
        self.actions = [
            action() if inspect.isclass(action) and issubclass(action, Action) else action
            for action in actions]

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

@cython.final
cdef class And:
    """
    `And` predicate. Exits at the first sub-predicate that returns ``False``.
    """
    cdef readonly tuple predicates

    def __init__(self, *predicates):
        self.predicates = predicates

    def __str__(self):
        return "And({})".format(', '.join(str(p) for p in self.predicates))

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

    def __richcmp__(self, other, int op):
        is_equal = isinstance(other, And) and self.predicates == (<And>other).predicates

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
        return "Or({})".format(', '.join(str(p) for p in self.predicates))

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

    def __richcmp__(self, other, int op):
        is_equal = isinstance(other, Or) and self.predicates == (<Or>other).predicates

        if op == Py_EQ:
            return is_equal
        if op == Py_NE:
            return not is_equal
        return PyObject_RichCompare(id(self), id(other), op)

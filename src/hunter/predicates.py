from __future__ import absolute_import

import inspect
from itertools import chain

from fields import Fields
from six import string_types

from .actions import Action
from .event import Event


class Query(Fields.query):
    """
    A query class.

    See :class:`hunter.Event` for fields that can be filtered on.
    """
    query = ()
    allowed = tuple(i for i in Event.__dict__.keys() if not i.startswith('_'))

    def __init__(self, **query):
        """
        Args:
            query: criteria to match on.

                Accepted arguments: ``arg``, ``code``, ``filename``, ``frame``, ``fullsource``, ``function``,
                ``globals``, ``kind``, ``lineno``, ``locals``, ``module``, ``source``, ``stdlib``, ``tracer``.
        """
        for key in query:
            if key not in self.allowed:
                raise TypeError("Unexpected argument {!r}. Must be one of {}.".format(key, self.allowed))
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
        else:
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
            raise TypeError("Must give at least one action.")
        super(When, self).__init__(condition, [
            action() if inspect.isclass(action) and issubclass(action, Action) else action
            for action in actions
            ])

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
        else:
            return True

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(*chain(self.predicates, other.predicates if isinstance(other, And) else (other,)))

    def __invert__(self):
        return Not(self)


class Or(Fields.predicates):
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
        for predicate in self.predicates:
            if predicate(event):
                return True
        else:
            return False

    def __or__(self, other):
        return Or(*chain(self.predicates, other.predicates if isinstance(other, Or) else (other,)))

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)


class Not(Fields.predicate):
    """
    `Not` predicate.
    """

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
        else:
            return Or(self, other)

    def __and__(self, other):
        if isinstance(other, Not):
            return Not(Or(self.predicate, other.predicate))
        else:
            return And(self, other)

    def __invert__(self):
        return self.predicate

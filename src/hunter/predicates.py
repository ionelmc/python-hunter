from __future__ import absolute_import

import inspect
from itertools import chain

from fields import Fields
from six import string_types

from .actions import CodePrinter

STARTSWITH_TYPES = (list, tuple, set)


def Q(*predicates, **query):
    """
    Handles situations where :class:`hunter.Query` objects (or other callables) are passed in as positional arguments.
    Conveniently converts that to an :class:`hunter.Or` predicate.
    """
    optional_actions = query.pop("actions", [])
    if "action" in query:
        optional_actions.append(query.pop("action"))

    if predicates:
        predicates = tuple(
            p() if inspect.isclass(p) and issubclass(p, Action) else p
            for p in predicates
        )
        if any(isinstance(p, CodePrinter) for p in predicates):
            if CodePrinter in optional_actions:
                optional_actions.remove(CodePrinter)
        if query:
            predicates += Query(**query),

        result = Or(*predicates)
    else:
        result = Query(**query)

    if optional_actions:
        result = When(result, *optional_actions)

    return result


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
            if isinstance(evalue, string_types) and isinstance(value, STARTSWITH_TYPES):
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


def _with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""

    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(meta):
        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)

    return type.__new__(metaclass, 'temporary_class', (), {})


class _UnwrapSingleArgumentMetaclass(type):
    def __call__(cls, predicate, *predicates):
        if not predicates:
            return predicate
        else:
            all_predicates = []

            for p in chain((predicate,), predicates):
                if isinstance(p, cls):
                    all_predicates.extend(p.predicates)
                else:
                    all_predicates.append(p)
            return super(_UnwrapSingleArgumentMetaclass, cls).__call__(*all_predicates)


class And(_with_metaclass(_UnwrapSingleArgumentMetaclass, ~Fields.predicates)):
    """
    `And` predicate. Exits at the first sub-predicate that returns ``False``.
    """

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


class Or(_with_metaclass(_UnwrapSingleArgumentMetaclass, ~Fields.predicates)):
    """
    `Or` predicate. Exits at first sub-predicate that returns ``True``.
    """

    def __init__(self, *predicates):
        self.predicates = predicates

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

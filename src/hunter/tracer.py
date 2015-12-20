from __future__ import absolute_import

import sys

from .event import Event


class Tracer(object):
    """
    Trace object.

    """

    def __init__(self):
        self.__handler = None
        self.__previous = None

    def __str__(self):
        return "Tracer(handler={}, previous={})".format(
            "<stopped>" if self._handler is None else self.__handler,
            self.__previous,
        )

    def __call__(self, frame, kind, arg):
        """
        The settrace function.

        .. note::

            This always returns self (drills down) - as opposed to only drilling down when predicate(event) is True
            because it might
            match further inside.
        """
        if self.__handler is not None:
            self.__handler(Event(frame, kind, arg, self))
            return self

    def trace(self, predicate):
        """
        Starts tracing. Can be used as a context manager (with slightly incorrect semantics - it starts tracing
        before ``__enter__`` is
        called).

        Args:
            predicates (:class:`hunter.Q` instances): Runs actions if any of the given predicates match.
            options: Keyword arguments that are passed to :class:`hunter.Q`, for convenience.
        """
        self.__handler = predicate
        self.__previous = sys.gettrace()
        sys.settrace(self)
        return self

    def stop(self):
        """
        Stop tracing.
        """
        if self.__handler is not None:
            sys.settrace(self.__previous)
            self.__handler = self.__previous = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

from __future__ import absolute_import

import sys

from .event import Event


class Tracer(object):
    """
    Trace object.

    """

    def __init__(self):
        self._handler = None

    def __str__(self):
        return "Tracer(_handler={})".format(
            "<stopped>" if self._handler is None else self._handler,
        )

    def __call__(self, frame, kind, arg):
        """
        The settrace function.

        .. note::

            This always returns self (drills down) - as opposed to only drilling down when predicate(event) is True
            because it might
            match further inside.
        """
        if self._handler is None:
            raise RuntimeError("Tracer is stopped.")

        self._handler(Event(frame, kind, arg, self))
        return self

    def trace(self, predicate, merge=False):
        """
        Starts tracing. Can be used as a context manager (with slightly incorrect semantics - it starts tracing
        before ``__enter__`` is
        called).

        Args:
            predicates (:class:`hunter.Q` instances): Runs actions if any of the given predicates match.
            options: Keyword arguments that are passed to :class:`hunter.Q`, for convenience.
        """
        if merge:
            self._handler |= predicate
        else:
            self._handler = predicate

        sys.settrace(self)

    def stop(self):
        """
        Stop tracing. Restores previous tracer (if any).
        """
        sys.settrace(None)
        self._handler = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

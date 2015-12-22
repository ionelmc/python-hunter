from __future__ import absolute_import

import sys

from .event import Event


class Tracer(object):
    """
    Trace object.

    """

    def __init__(self):
        self._handler = None
        self._previous = None

    def __repr__(self):
        return '<hunter.tracer.Tracer at 0x%x: %s%s%s%s>' % (
            id(self),
            '<stopped>' if self._handler is None else 'handler=',
            '' if self._handler is None else repr(self._handler),
            '' if self._previous is None else ', previous=',
            '' if self._previous is None else repr(self._previous),
        )

    def __call__(self, frame, kind, arg):
        """
        The settrace function.

        .. note::

            This always returns self (drills down) - as opposed to only drilling down when predicate(event) is True
            because it might match further inside.
        """
        if self._handler is not None:
            self._handler(Event(frame, kind, arg, self))
            return self

    def trace(self, predicate):
        self._handler = predicate
        self._previous = sys.gettrace()
        sys.settrace(self)
        return self

    def stop(self):
        if self._handler is not None:
            sys.settrace(self._previous)
            self._handler = self._previous = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

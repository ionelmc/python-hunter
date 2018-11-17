from __future__ import absolute_import

import sys
import threading

from .event import Event


class Tracer(object):
    """
    Trace object.

    """

    def __init__(self, threading_support=None):
        self._handler = None
        self._previous = None
        self._threading_previous = None
        self.threading_support = threading_support
        self.depth = 0
        self.calls = 0

    @property
    def handler(self):
        return self._handler

    @property
    def previous(self):
        return self._previous

    def __repr__(self):
        return '<hunter.tracer.Tracer at 0x%x: threading_support=%s, %s%s%s%s>' % (
            id(self),
            self.threading_support,
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
            if kind == 'call':
                self.depth += 1
                self.calls += 1
            elif kind == 'return':
                self.depth -= 1

            return self

    def trace(self, predicate):
        self._handler = predicate
        if self.threading_support is None or self.threading_support:
            self._threading_previous = getattr(threading, '_trace_hook', None)
            threading.settrace(self)
        self._previous = sys.gettrace()
        sys.settrace(self)
        return self

    def stop(self):
        if self._handler is not None:
            sys.settrace(self._previous)
            self._handler = self._previous = None
            if self.threading_support is None or self.threading_support:
                threading.settrace(self._threading_previous)
                self._threading_previous = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

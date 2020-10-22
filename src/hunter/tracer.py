from __future__ import absolute_import

import sys
import threading
import traceback

import hunter

from .event import Event

__all__ = 'Tracer',


class Tracer(object):
    """
    Tracer object.

    Args:
        threading_support (bool): Hooks the tracer into ``threading.settrace`` as well if True.
    """
    def __init__(self, threading_support=None, profiling_mode=False):
        self._handler = None
        self._previous = None
        self._threading_previous = None

        #: True if threading support was enabled. Should be considered read-only.
        #:
        #: :type: bool
        self.threading_support = threading_support

        #: True if profiling mode was enabled. Should be considered read-only.
        #:
        #: :type: bool
        self.profiling_mode = profiling_mode

        #: Tracing depth (increases on calls, decreases on returns)
        #:
        #: :type: int
        self.depth = 0

        #: A counter for total number of 'call' frames that this Tracer went through.
        #:
        #: :type: int
        self.calls = 0

    @property
    def handler(self):
        """
        The current predicate. Set via :func:`hunter.Tracer.trace`.
        """
        return self._handler

    @property
    def previous(self):
        """
        The previous tracer, if any (whatever ``sys.gettrace()`` returned prior to :func:`hunter.Tracer.trace`).
        """
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

            This always returns self (drills down) - as opposed to only drilling down when ``predicate(event)`` is True
            because it might match further inside.
        """
        if self._handler is not None:
            if kind == 'return' and self.depth > 0:
                self.depth -= 1
            event = Event(frame, kind, arg, self)
            try:
                self._handler(event)
            except Exception as exc:
                traceback.print_exc(file=hunter._default_stream)
                hunter._default_stream.write('Disabling tracer because handler %r failed (%r) at %r.\n\n' % (
                    self._handler, exc, event))
                self.stop()
                return
            if kind == 'call':
                self.depth += 1
                self.calls += 1

            return self

    def trace(self, predicate):
        """
        Starts tracing with the given callable.

        Args:
            predicate (callable that accepts a single :obj:`~hunter.event.Event` argument):
        Return:
            self
        """
        self._handler = predicate
        if self.profiling_mode:
            if self.threading_support is None or self.threading_support:
                self._threading_previous = getattr(threading, '_profile_hook', None)
                threading.setprofile(self)
            self._previous = sys.getprofile()
            sys.setprofile(self)
        else:
            if self.threading_support is None or self.threading_support:
                self._threading_previous = getattr(threading, '_trace_hook', None)
                threading.settrace(self)
            self._previous = sys.gettrace()
            sys.settrace(self)
        return self

    def stop(self):
        """
        Stop tracing. Reinstalls the :attr:`~hunter.tracer.Tracer.previous` tracer.
        """
        if self._handler is not None:
            if self.profiling_mode:
                sys.setprofile(self._previous)
                self._handler = self._previous = None
                if self.threading_support is None or self.threading_support:
                    threading.setprofile(self._threading_previous)
                    self._threading_previous = None
            else:
                sys.settrace(self._previous)
                self._handler = self._previous = None
                if self.threading_support is None or self.threading_support:
                    threading.settrace(self._threading_previous)
                    self._threading_previous = None

    def __enter__(self):
        """
        Does nothing. Users are expected to call :meth:`~hunter.tracer.Tracer.trace`.

        Returns: self
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Wrapper around :meth:`~hunter.tracer.Tracer.stop`. Does nothing with the arguments.
        """
        self.stop()

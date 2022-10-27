# cython: language_level=3str, c_string_encoding=ascii
cimport cython

import hunter

from hunter._event cimport Event
from hunter._event cimport fast_detach


@cython.final
cdef class EvilTracer:
    is_pure = False

    cdef readonly object _calls
    cdef readonly object handler
    cdef readonly object _tracer
    cdef readonly int _stopped

    def __init__(self, *args, **kwargs):
        self._calls = []
        threading_support = kwargs.pop('threading_support', False)
        clear_env_var = kwargs.pop('clear_env_var', False)
        self.handler = hunter._prepare_predicate(*args, **kwargs)
        self._tracer = hunter.trace(self._append, threading_support=threading_support, clear_env_var=clear_env_var)
        self._stopped = False

    def _append(self, Event event):
        if self._stopped:
            return
        detached_event = fast_detach(event, lambda obj: obj)
        detached_event.detached = False
        self._calls.append(detached_event)

    def __enter__(self):
        self._stopped = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stopped = True
        self._tracer.stop()
        predicate = self.handler
        for call in self._calls:
            predicate(call)

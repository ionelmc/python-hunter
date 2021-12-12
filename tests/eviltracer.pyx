# language_level=3
import cython

from cpython.pystate cimport PyThreadState
from cpython.pystate cimport PyThreadState_Get

import hunter

from hunter._event cimport Event
from hunter._event cimport fast_detach


cdef extern from "frameobject.h":
    ctypedef struct PyObject

    ctypedef class types.CodeType[object PyCodeObject]:
        cdef object co_filename
        cdef int co_firstlineno

    ctypedef class types.FrameType[object PyFrameObject]:
        cdef CodeType f_code
        cdef FrameType f_back
        cdef int f_lasti
        cdef int f_lineno
        cdef object f_globals
        cdef object f_locals
        cdef PyObject *f_trace

    cdef FrameType PyFrame_New(PyThreadState*, CodeType, object, object)

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
        frame = PyFrame_New(PyThreadState_Get(), <CodeType>event.code, event.frame.f_globals, event.frame.f_locals)
        frame.f_back = event.frame.f_back
        frame.f_lasti = event.frame.f_lasti
        frame.f_lineno = 0
        detached_event.frame = frame

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

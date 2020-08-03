# cython: linetrace=True, language_level=3str
import threading
import traceback

from cpython cimport pystate
from cpython.pystate cimport PyThreadState_Get
from cpython.ref cimport Py_CLEAR
from cpython.ref cimport Py_INCREF

from ._event cimport Event
from ._predicates cimport From
from ._predicates cimport When
from ._predicates cimport fast_call

import hunter

__all__ = 'Tracer',

cdef dict KIND_INTS = {
    'call': 0,
    'exception': 1,
    'line': 2,
    'return': 3,
    'c_call': 4,
    'c_exception': 5,
    'c_return': 6,
}

cdef int trace_func(Tracer self, FrameType frame, int kind, PyObject *arg) except -1:
    if frame.f_trace is not <PyObject*> self:
        Py_CLEAR(frame.f_trace)
        Py_INCREF(self)
        frame.f_trace = <PyObject*> self

    handler = self.handler

    if kind == 3 and self.depth > 0:
        self.depth -= 1

    cdef Event event = Event(frame, kind, None if arg is NULL else <object>arg, self)

    try:
        fast_call(handler, event)
    except Exception as exc:
        traceback.print_exc(file=hunter._default_stream)
        hunter._default_stream.write('Disabling tracer because handler {} failed ({!r}).\n\n'.format(
            handler, exc))
        self.stop()
        return 0

    if kind == 0:
        self.depth += 1
        self.calls += 1


cdef class Tracer:
    def __cinit__(self, threading_support=None, profiling_mode=False):
        self.handler = None
        self.previous = None
        self._previousfunc = NULL
        self._threading_previous = None
        self.threading_support = threading_support
        self.profiling_mode = profiling_mode
        self.depth = 0
        self.calls = 0

    def __dealloc__(self):
        cdef PyThreadState *state = PyThreadState_Get()
        if state.c_traceobj is <PyObject *>self:
            self.stop()

    def __repr__(self):
        return '<hunter._tracer.Tracer at 0x%x: threading_support=%s, %s%s%s%s>' % (
            id(self),
            self.threading_support,
            '<stopped>' if self.handler is None else 'handler=',
            '' if self.handler is None else repr(self.handler),
            '' if self.previous is None else ', previous=',
            '' if self.previous is None else repr(self.previous),
        )

    def __call__(self, FrameType frame, str kind, arg):
        trace_func(self, frame, KIND_INTS[kind], <PyObject *> arg)
        if kind == 0:
            PyEval_SetTrace(<pystate.Py_tracefunc> trace_func, <PyObject *> self)
        return self

    def trace(self, predicate):
        self.handler = predicate
        cdef PyThreadState *state = PyThreadState_Get()

        if self.profiling_mode:
            if self.threading_support is None or self.threading_support:
                self._threading_previous = getattr(threading, '_profile_hook', None)
                threading.setprofile(self)
            if state.c_profileobj is NULL:
                self.previous = None
                self._previousfunc = NULL
            else:
                self.previous = <object>(state.c_profileobj)
                self._previousfunc = state.c_profilefunc
            PyEval_SetProfile(<pystate.Py_tracefunc> trace_func, <PyObject *> self)
        else:
            if self.threading_support is None or self.threading_support:
                self._threading_previous = getattr(threading, '_trace_hook', None)
                threading.settrace(self)
            if state.c_traceobj is NULL:
                self.previous = None
                self._previousfunc = NULL
            else:
                self.previous = <object>(state.c_traceobj)
                self._previousfunc = state.c_tracefunc
            PyEval_SetTrace(<pystate.Py_tracefunc> trace_func, <PyObject *> self)
        return self

    def stop(self):
        if self.handler is not None:
            if self.profiling_mode:
                if self.previous is None:
                    PyEval_SetProfile(NULL, NULL)
                else:
                    PyEval_SetProfile(self._previousfunc, <PyObject *> self.previous)
                self.handler = self.previous = None
                self._previousfunc = NULL
                if self.threading_support is None or self.threading_support:
                    threading.setprofile(self._threading_previous)
                    self._threading_previous = None
            else:
                if self.previous is None:
                    PyEval_SetTrace(NULL, NULL)
                else:
                    PyEval_SetTrace(self._previousfunc, <PyObject *> self.previous)
                self.handler = self.previous = None
                self._previousfunc = NULL
                if self.threading_support is None or self.threading_support:
                    threading.settrace(self._threading_previous)
                    self._threading_previous = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

# cython: linetrace=True, language_level=3str, freethreading_compatible=True
import threading
import traceback

from cpython.pystate cimport PyThreadState_Get
from cpython.pystate cimport PyFrameObject
from ._event cimport Event
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

cdef int trace_func(PyObject* tracer, PyFrameObject* frame, int kind, PyObject* arg) noexcept:
    cdef Tracer self = <Tracer?> tracer
    cdef FrameType frame_object = <FrameType> frame

    frame_object.f_trace = self
    handler = self.handler

    if handler is None:  # the tracer was stopped
        # make sure it's uninstalled even for running threads
        if self.profiling_mode:
            PyEval_SetProfile(NULL, NULL)
        else:
            PyEval_SetTrace(NULL, NULL)
        return 0

    if kind == 3 and self.depth > 0:
        self.depth -= 1

    cdef Event event = Event(<FrameType> frame, kind, None if arg is NULL else <object> arg, self.depth, self.calls, self.threading_support)
    try:
        fast_call(handler, event)
    except Exception as exc:
        traceback.print_exc(file=hunter._default_stream)
        hunter._default_stream.write('Disabling tracer because handler %r failed (%r) at %r.\n\n' % (
            handler, exc, event))
        self.stop()
        return 0

    if kind == 0:
        self.depth += 1
        self.calls += 1
    return 0


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
        if state.c_traceobj is <PyObject*> self:
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

    def __call__(self, frame, str kind, arg):
        trace_func(<PyObject*> self, <PyFrameObject*> frame, KIND_INTS[kind], <PyObject*> arg)
        if kind == 0:
            PyEval_SetTrace(trace_func, <PyObject*> self)
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
            PyEval_SetProfile(trace_func, <PyObject*> self)
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
            PyEval_SetTrace(trace_func, <PyObject*> self)
        return self

    def stop(self):
        if self.handler is not None:
            if self.profiling_mode:
                if self.previous is None:
                    PyEval_SetProfile(NULL, NULL)
                else:
                    PyEval_SetProfile(self._previousfunc, <PyObject*> self.previous)
                self.handler = self.previous = None
                self._previousfunc = NULL
                if self.threading_support is None or self.threading_support:
                    threading.setprofile(self._threading_previous)
                    self._threading_previous = None
            else:
                if self.previous is None:
                    PyEval_SetTrace(NULL, NULL)
                else:
                    PyEval_SetTrace(self._previousfunc, <PyObject*> self.previous)
                self.handler = self.previous = None
                self._previousfunc = NULL
                if self.threading_support is None or self.threading_support:
                    threading.settrace(self._threading_previous)
                    self._threading_previous = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

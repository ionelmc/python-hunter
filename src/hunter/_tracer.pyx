# cython: linetrace=True
import threading

from cpython cimport pystate
from cpython.ref cimport Py_INCREF
from cpython.ref cimport Py_XDECREF
from cpython.pystate cimport PyThreadState_Get

from ._event cimport Event
from ._predicates cimport When
from ._predicates cimport fast_When_call
from ._predicates cimport And
from ._predicates cimport fast_And_call
from ._predicates cimport Or
from ._predicates cimport fast_Or_call
from ._predicates cimport Not
from ._predicates cimport fast_Not_call

cdef tuple kind_names = ("call", "exception", "line", "return", "c_call", "c_exception", "c_return")


cdef int trace_func(Tracer self, FrameType frame, int kind, PyObject *arg) except -1:
    if frame.f_trace is not <PyObject*> self:
        junk = frame.f_trace
        Py_INCREF(self)
        frame.f_trace = <PyObject*> self
        Py_XDECREF(junk)

    handler = self.handler
    if type(handler) is When:
        fast_When_call(<When>handler, Event(frame, kind_names[kind], None if arg is NULL else <object>arg, self))
    elif type(handler) is And:
        fast_And_call(<And>handler, Event(frame, kind_names[kind], None if arg is NULL else <object>arg, self))
    elif type(handler) is Or:
        fast_Or_call(<Or>handler, Event(frame, kind_names[kind], None if arg is NULL else <object>arg, self))
    elif type(handler) is Not:
        fast_Not_call(<Not>handler, Event(frame, kind_names[kind], None if arg is NULL else <object>arg, self))
    elif handler is not None:
        handler(Event(frame, kind_names[kind], None if arg is NULL else <object>arg, self))

    if kind == 0:
        self.depth += 1
        self.calls += 1
    elif kind == 3:
        self.depth -= 1


cdef class Tracer:
    """
    Tracer object.

    """
    def __cinit__(self, threading_support=False):
        self.handler = None
        self.previous = None
        self._previousfunc = NULL
        self._threading_previous = None
        self.threading_support = threading_support
        self.depth = 1
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

    def __call__(self, frame, kind, arg):
        """
        The settrace function.

        .. note::

            This always returns self (drills down) - as opposed to only drilling down when predicate(event) is True
            because it might match further inside.
        """
        trace_func(self, frame, kind_names.index(kind), <PyObject *> arg)
        if kind == "call":
            PyEval_SetTrace(<pystate.Py_tracefunc> trace_func, <PyObject *> self)
        return self

    def trace(self, predicate):
        cdef PyThreadState *state = PyThreadState_Get()
        self.handler = predicate
        if self.threading_support:
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
            if self.previous is None:
                PyEval_SetTrace(NULL, NULL)
            else:
                PyEval_SetTrace(self._previousfunc, <PyObject *> self.previous)
            self.handler = self.previous = None
            self._previousfunc = NULL
            if self.threading_support:
                threading.settrace(self._threading_previous)
                self._threading_previous = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

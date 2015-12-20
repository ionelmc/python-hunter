from sys import settrace

from cpython cimport pystate
from cpython.ref cimport Py_INCREF
from cpython.ref cimport Py_XDECREF

from ._event cimport Event

cdef tuple kind_names = ("call", "exception", "line", "return", "c_call", "c_exception", "c_return")

cdef int trace_func(Tracer self, FrameType frame, int kind, PyObject *arg) except -1:
    if frame.f_trace is not <PyObject*> self:
        junk = frame.f_trace
        Py_INCREF(self)
        frame.f_trace = <PyObject*> self
        Py_XDECREF(junk)

    if self._handler is not None:
        self._handler(Event(frame, kind_names[kind], None if arg is NULL else <object>arg, self))

cdef class Tracer:
    """
    Tracer object.

    """
    def __cinit__(self):
        self._handler = None
        self._previous = None

    def __repr__(self):
        return '<hunter._tracer.Tracer at 0x%x: %s%s%s%s>' % (
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
            because it might
            match further inside.
        """
        trace_func(self, frame, kind_names.index(kind), <PyObject *> arg)
        if kind == "call":
            PyEval_SetTrace(<pystate.Py_tracefunc> trace_func, <PyObject *> self)
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
        self._handler = predicate
        previous = PyThreadState_Get()
        if previous.c_traceobj is NULL:
            self._previous = None
        else:
            self._previous = <object>previous.c_traceobj
        PyEval_SetTrace(<pystate.Py_tracefunc> trace_func, <PyObject *> self)
        return self

    def stop(self):
        """
        Stop tracing.
        """
        if self._handler is not None:
            if self._previous is None:
                PyEval_SetTrace(NULL, NULL)
            else:
                settrace(self._previous)
            self._handler = self._previous = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

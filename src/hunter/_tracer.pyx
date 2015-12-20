from cpython cimport pystate
from cpython.ref cimport Py_INCREF
from cpython.ref cimport Py_XDECREF

from ._event cimport Event

cdef tuple kind_names = ("call", "exception", "line", "return", "c_call", "c_exception", "c_return")

cdef int trace_func(Tracer self, FrameType frame, int kind, object arg) except -1:
    if frame.f_trace is not self:
        junk = <PyObject*>frame.f_trace
        Py_INCREF(self)
        frame.f_trace = self
        Py_XDECREF(junk)

    if self._handler is None:
        raise RuntimeError("Tracer is stopped.")
    else:
        self._handler(Event(frame, kind, arg, self))

cdef class Tracer:
    """
    Tracer object.

    """
    def __cinit__(self):
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
        trace_func(self, frame, kind_names.index(kind), arg)
        if kind == "call":
            PyEval_SetTrace(<pystate.Py_tracefunc>trace_func, <PyObject *>self)
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
        PyEval_SetTrace(<pystate.Py_tracefunc>trace_func, <PyObject *>self)
        return self

    def stop(self):
        """
        Stop tracing.
        """
        if self._handler is not None:
            PyEval_SetTrace(NULL, NULL)
            self._handler = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

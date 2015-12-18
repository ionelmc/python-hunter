cimport cython

from ._tracer cimport *

@cython.final
cdef class Event:
    """
    Event wrapper for ``frame, kind, arg`` (the arguments the settrace function gets).

    Provides few convenience properties.
    """
    cdef:
        FrameType frame
        public str kind
        public object arg
        public Tracer tracer
        object _module
        object _filename
        object _fullsource
        object _source

    cdef object _get_globals(self)
    cdef object _get_locals(self)

cimport cython

from ._tracer cimport *


cdef extern from "frameobject.h":
    void PyFrame_FastToLocals(FrameType)

@cython.final
cdef class Event:
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

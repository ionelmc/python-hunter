cimport cython

from ._tracer cimport *


cdef extern from "frameobject.h":
    void PyFrame_FastToLocals(FrameType)

@cython.final
cdef class Event:
    cdef:
        readonly FrameType frame
        readonly str kind
        readonly object arg
        readonly Tracer tracer

        object _module
        object _filename
        object _fullsource
        object _source

    cdef object _get_globals(self)
    cdef object _get_locals(self)

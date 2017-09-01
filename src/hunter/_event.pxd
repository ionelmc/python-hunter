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
        readonly int depth
        readonly int calls
        readonly Tracer tracer

        object _filename
        object _fullsource
        object _lineno
        object _module
        object _source
        object _stdlib
        object _thread
        object _threadidn  # slightly different name cause "_threadid" is a goddamn macro in Microsoft stddef.h
        object _threadname

    cdef object _get_globals(self)

    cdef object _get_locals(self)

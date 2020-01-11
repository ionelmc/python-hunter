# cython: language_level=3str
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
        readonly bint threading_support
        readonly bint detached

        object _code
        object _filename
        object _fullsource
        object _function
        object _function_object
        object _globals
        object _lineno
        object _locals
        object _module
        object _source
        object _stdlib
        object _thread
        object _threadidn  # slightly different name cause "_threadid" is a goddamn macro in Microsoft stddef.h
        object _threadname

        Event clone(self)

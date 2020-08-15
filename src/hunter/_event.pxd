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
        readonly object builtin

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
        object _instruction

        object code_getter(self)
        object filename_getter(self)
        object fullsource_getter(self)
        object function_getter(self)
        object globals_getter(self)
        object lineno_getter(self)
        object locals_getter(self)
        object module_getter(self)
        object source_getter(self)
        object stdlib_getter(self)
        object threadid_getter(self)
        object threadname_getter(self)
        object instruction_getter(self)

cdef Event fast_clone(Event self)
cdef Event fast_detach(Event self, object value_filter)

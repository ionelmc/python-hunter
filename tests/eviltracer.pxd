# cython: language_level=3str
cimport cython


cdef extern from "vendor/_compat.h":
    """
    #if PY_VERSION_HEX >= 0x030B00A7
    #define Py_BUILD_CORE
    #include "internal/pycore_frame.h"
    #endif
    """

    ctypedef struct PyObject

    ctypedef class types.FrameType[object PyFrameObject, check_size ignore]:
        pass


@cython.final
cdef class EvilTracer:
    cdef readonly object _calls
    cdef readonly object handler
    cdef readonly object _tracer
    cdef readonly int _stopped

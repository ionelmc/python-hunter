cimport cython


cdef extern from "vendor/_compat.h":
    """
    #if PY_VERSION_HEX >= 0x030900A4
    #include "internal/pycore_frame.h"
    #endif
    """


@cython.final
cdef class EvilTracer:
    cdef readonly object _calls
    cdef readonly object handler
    cdef readonly object _tracer
    cdef readonly int _stopped

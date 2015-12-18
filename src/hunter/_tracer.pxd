cimport cython
from cpython cimport pystate

cdef extern from "frameobject.h":
    ctypedef struct PyObject

    ctypedef class types.CodeType[object PyCodeObject]:
        cdef object co_filename
        cdef int co_firstlineno

    ctypedef class types.FrameType[object PyFrameObject]:
        cdef CodeType f_code
        cdef PyObject *f_back
        cdef PyObject *f_trace
        cdef int f_lineno

    void PyEval_SetTrace(pystate.Py_tracefunc func, PyObject*obj)

@cython.final
cdef class Tracer:
    """
    Tracer object.

    """
    cdef:
        public object _handler
        public object _previous_tracer

cimport cython
from cpython cimport pystate

cdef extern from "frameobject.h":
    ctypedef struct PyObject

    ctypedef class types.CodeType[object PyCodeObject]:
        cdef object co_filename
        cdef int co_firstlineno

    ctypedef class types.FrameType[object PyFrameObject]:
        cdef CodeType f_code
        cdef PyObject *f_trace
        cdef object f_globals
        cdef object f_locals
        cdef int f_lineno

    void PyEval_SetTrace(pystate.Py_tracefunc func, PyObject *obj)

cdef extern from "pystate.h":
    ctypedef struct PyThreadState:
        PyObject *c_traceobj

    PyThreadState* PyThreadState_Get()

@cython.final
cdef class Tracer:
    cdef:
        readonly object _handler
        readonly object _previous

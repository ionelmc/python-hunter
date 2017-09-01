cimport cython
from cpython cimport bool
from cpython.pystate cimport Py_tracefunc


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

    void PyEval_SetTrace(Py_tracefunc func, PyObject *obj)


cdef extern from "pystate.h":
    ctypedef struct PyThreadState:
        PyObject *c_traceobj
        Py_tracefunc c_tracefunc



@cython.final
cdef class Tracer:
    cdef:
        readonly object handler
        readonly object previous
        readonly bool threading_support
        readonly int depth
        readonly int calls

        object __weakref__

        readonly object _threading_previous
        Py_tracefunc _previousfunc

# cython: language_level=3str
cimport cython
from cpython.pystate cimport Py_tracefunc


cdef extern from "frameobject.h":
    ctypedef struct PyObject

    ctypedef class types.CodeType[object PyCodeObject]:
        cdef object co_filename
        cdef object co_code
        cdef int co_firstlineno

    ctypedef class types.FrameType[object PyFrameObject]:
        cdef CodeType f_code
        cdef PyObject *f_trace
        cdef object f_globals
        cdef object f_locals
        cdef int f_lineno
        cdef int f_lasti

    void PyEval_SetTrace(Py_tracefunc func, PyObject *obj)
    void PyEval_SetProfile(Py_tracefunc func, PyObject *obj)

cdef extern from "pystate.h":
    ctypedef struct PyThreadState:
        PyObject *c_traceobj
        PyObject *c_profileobj
        Py_tracefunc c_tracefunc
        Py_tracefunc c_profilefunc

@cython.final
cdef class Tracer:
    cdef:
        readonly object handler
        readonly object previous
        readonly object threading_support
        readonly bint profiling_mode
        readonly int depth
        readonly int calls

        object __weakref__

        readonly object _threading_previous
        Py_tracefunc _previousfunc

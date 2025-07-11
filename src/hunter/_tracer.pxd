cimport cython
from cpython.pystate cimport Py_tracefunc
from cpython.ref cimport PyObject


ctypedef extern FrameType

cdef extern from *:
    void PyEval_SetTrace(Py_tracefunc, PyObject*)
    void PyEval_SetProfile(Py_tracefunc, PyObject*)

    ctypedef extern class types.CodeType[object PyCodeObject, check_size ignore]:
        cdef object co_filename
        cdef object co_name
        cdef int co_argcount

cdef extern from "pystate.h":
    ctypedef struct PyThreadState:
        PyObject* c_traceobj
        PyObject* c_profileobj
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

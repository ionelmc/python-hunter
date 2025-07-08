# cython: language_level=3str
cimport cython
from cpython.pystate cimport Py_tracefunc
from cpython.pystate cimport PyFrameObject
from cpython.ref cimport PyObject

ctypedef extern FrameType

cdef extern from "vendor/_compat.h":
    """
    static inline PyCodeObject* Hunter_PyFrame_GetCode(PyObject* frame) {
        return PyFrame_GetCode((PyFrameObject*) frame);
    }
    static inline int Hunter_PyFrame_GetLasti(PyObject* frame) {
        return PyFrame_GetLasti((PyFrameObject*) frame);
    }
    static inline int Hunter_PyFrame_GetLineNumber(PyObject* frame) {
        return PyFrame_GetLineNumber((PyFrameObject*) frame);
    }
    static inline PyObject* Hunter_PyFrame_GetGlobals(PyObject* frame) {
        return PyFrame_GetGlobals((PyFrameObject*) frame);
    }
    static inline PyObject* Hunter_PyFrame_GetLocals(PyObject* frame) {
        return PyFrame_GetLocals((PyFrameObject*) frame);
    }
    """
    object PyCode_GetCode(CodeType)
    object PyCode_GetVarnames(CodeType)
    CodeType Hunter_PyFrame_GetCode(FrameType frame)
    int Hunter_PyFrame_GetLasti(FrameType frame)
    int Hunter_PyFrame_GetLineNumber(FrameType frame)
    object Hunter_PyFrame_GetGlobals(FrameType frame)
    object Hunter_PyFrame_GetLocals(FrameType frame)


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

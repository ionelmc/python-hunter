cimport cython


ctypedef extern FrameType

cdef extern from *:
    ctypedef extern class types.CodeType[object PyCodeObject, check_size ignore]:
        cdef object co_filename
        cdef object co_name
        cdef int co_argcount

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

        CodeType code_getter(self)
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

# cython: language_level=3str
from ._event cimport Event


cdef class Action:
    cdef:
        pass

cdef class Debugger(Action):
    cdef:
        public object klass
        public dict kwargs

cdef class Manhole(Action):
    cdef:
        public dict options

cdef class ColorStreamAction(Action):
    cdef:
        public bint force_colors
        public bint force_pid
        public int filename_alignment
        public int thread_alignment
        public int pid_alignment
        public int repr_limit
        public set seen_threads
        public int seen_pid

        object _repr_func

        # set via stream property
        bint _tty
        object _stream
        public dict event_colors
        public dict code_colors

    cdef _try_repr(self, obj)
    cdef _format_filename(self, event)

cdef class CodePrinter(ColorStreamAction):
    cdef _safe_source(self, event)

cdef class CallPrinter(CodePrinter):
    cdef:
        public object locals

cdef class VarsPrinter(ColorStreamAction):
    cdef:
        public dict names

cdef class VarsSnooper(ColorStreamAction):
    cdef:
        public object stored_reprs

cdef fast_CodePrinter_call(CodePrinter self, Event event)
cdef fast_CallPrinter_call(CallPrinter self, Event event)
cdef fast_VarsPrinter_call(VarsPrinter self, Event event)
cdef fast_VarsSnooper_call(VarsSnooper self, Event event)

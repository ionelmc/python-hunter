cimport cython

@cython.final
cdef class When:
    cdef:
        readonly object condition
        readonly list actions

cdef inline fast_When_call(When self, event)

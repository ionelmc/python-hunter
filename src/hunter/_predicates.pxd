cimport cython


@cython.final
cdef class Query:
    cdef:
        readonly tuple query_eq
        readonly tuple query_startswith
        readonly tuple query_endswith
        readonly tuple query_in
        readonly tuple query_contains
        readonly tuple query_regex
        readonly tuple query_lt
        readonly tuple query_lte
        readonly tuple query_gt
        readonly tuple query_gte

@cython.final
cdef class And:
    cdef:
        readonly tuple predicates

@cython.final
cdef class Or:
    cdef:
        readonly tuple predicates

@cython.final
cdef class Not:
    cdef:
        readonly object predicate

@cython.final
cdef class When:
    cdef:
        readonly object condition
        readonly tuple actions

cdef fast_When_call(When self, event)
cdef fast_And_call(And self, event)
cdef fast_Or_call(Or self, event)
cdef fast_Not_call(Not self, event)

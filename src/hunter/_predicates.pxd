# cython: language_level=3str
cimport cython

from ._event cimport Event


@cython.final
cdef class Query:
    cdef:
        readonly tuple query_contains
        readonly tuple query_endswith
        readonly tuple query_eq
        readonly tuple query_gt
        readonly tuple query_gte
        readonly tuple query_in
        readonly tuple query_lt
        readonly tuple query_lte
        readonly tuple query_regex
        readonly tuple query_startswith


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


@cython.final
cdef class From:
    cdef:
        readonly object condition
        readonly object predicate
        readonly int watermark
        readonly int origin_depth
        readonly int origin_calls


@cython.final
cdef class Backlog:
    cdef:
        readonly object condition
        readonly int size
        readonly int stack
        readonly bint vars
        readonly bint strip
        readonly object action
        readonly object _try_repr
        readonly object _filter
        readonly object queue

cdef fast_And_call(And self, Event event)
cdef fast_From_call(From self, Event event)
cdef fast_Not_call(Not self, Event event)
cdef fast_Or_call(Or self, Event event)
cdef fast_Query_call(Query self, Event event)
cdef fast_When_call(When self, Event event)
cdef fast_call(object callable, Event event)

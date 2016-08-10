# cython: linetrace=True
foo = bar = lambda x: x

@foo
@bar
def foo():
    return 1


# cython: linetrace=True, language_level=3
foo = bar = lambda x: x

@foo
@bar
def foo():
    return 1

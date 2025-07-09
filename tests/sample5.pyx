# cython: linetrace=True, language_level=3str, freethreading_compatible=True
a = b = lambda x: x


@a
@b
def foo():
    return 1


def bar():
    foo()

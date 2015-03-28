""" s@tart
1
2
3
4
"""  # end
class Foo(object):

    @staticmethod
    def a(*args):
        return args

    b = staticmethod(
        lambda *a:
            a
    )


def deco(_):
    return lambda func: lambda *a: func(*a)


@deco(1)
@deco(2)
@deco(3)
@deco(4)
def a(*args):
    return args


Foo.a(
    1,
    2,
    3,
)
Foo.b(
    1,
    2,
    3,
)
a()

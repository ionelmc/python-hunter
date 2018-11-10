class Bad:
    __slots__ = []

    def __repr__(self):
        raise RuntimeError("I'm a bad class!")


def a():
    x = Bad()
    return x


def b():
    x = Bad()
    raise Exception(x)

a()
try:
    b()
except Exception as exc:
    print(exc)

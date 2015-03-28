class Bad(Exception):
    def __repr__(self):
        raise RuntimeError("I'm a bad class!")


def a():
    x = Bad()
    return x

def b():
    x = Bad()
    raise x

a()
try:
    b()
except Exception as exc:
    print(exc)

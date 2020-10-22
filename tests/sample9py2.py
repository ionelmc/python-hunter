from inspect import CO_VARKEYWORDS


def foo(a, (b,), (c, d), (e, (f, g), h)):
    print(a, b, c, d, e, f, g , h)

if __name__ == "__main__":
    foo(1, (2, ), (3, 4), (5, (6, 7), 8))

    import dis
    dis.dis(foo)

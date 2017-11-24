def bar():
    foo()


def foo():
    try:
        asdf()
    except:
        pass
    try:
        asdf()
    except:
        pass


def asdf():
    raise Exception()

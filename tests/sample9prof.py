from __future__ import print_function


class Foo:
    pass


obj = Foo()


def one():
    for i in range(1):  # one
        two()


def two():
    for i in range(1):  # two
        three()


def three():
    setattr(obj, 'attr', 3)  # asdf
    for i in range(1):  # three
        four()


def four():
    try:
        setattr(None, 'attr', 4)  # qwer
    except:
        pass
    for i in range(1):  # four
        five()


def five():
    in_five = 1
    setattr(obj, 'attr', 5)  # zxcv
    for i in range(1):  # five
        return i


if __name__ == "__main__":
    one()

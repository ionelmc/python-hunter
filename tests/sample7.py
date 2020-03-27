from __future__ import print_function


def one(a=123, b='234'):
    for i in range(1):  # one
        a = b = None
        two()


def two(c={'3': [4, 5]}):
    for i in range(1):  # two
        c['side'] = 'effect'
        three()


def three():
    for i in range(1):  # three
        four()


def four():
    for i in range(1):  # four
        five()


def five():
    in_five = 1
    for i in range(1):  # five
        return i  # five


if __name__ == "__main__":
    one()

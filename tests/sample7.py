from __future__ import print_function

import os
import sys


def one():
    for i in range(1):  # one
        two()


def two():
    for i in range(1):  # two
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
        return i


if __name__ == "__main__":
    one()

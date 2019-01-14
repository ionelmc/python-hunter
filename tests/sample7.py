from __future__ import print_function

import os
import sys


def one():
    for i in range(1):
        two()


def two():
    for i in range(1):
        three()


def three():
    for i in range(1):
        four()


def four():
    for i in range(1):
        five()


def five():
    for i in range(1):
        return i


if __name__ == "__main__":
    print('>>>>>>', os.environ.get('PYTHONHUNTER'))
    print('>>>>>>', sys.argv)
    one()

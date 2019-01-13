from __future__ import print_function

import os
import sys


def one():
    for i in range(2):
        two()


def two():
    for i in range(2):
        three()


def three():
    for i in range(2):
        four()


def four():
    for i in range(2):
        five()


def five():
    for i in range(10):
        pass


if __name__ == "__main__":
    print('>>>>>>', os.environ.get('PYTHONHUNTER'))
    print('>>>>>>', sys.argv)
    one()

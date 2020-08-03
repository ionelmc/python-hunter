from __future__ import print_function


def one(a=123, b='234', c={'3': [4, '5']}):
    for i in range(1):  # one
        a = b = c['side'] = 'effect'
        two()


def two(a=123, b='234', c={'3': [4, '5']}):
    for i in range(1):  # two
        a = b = c['side'] = 'effect'
        three()


def three(a=123, b='234', c={'3': [4, '5']}):
    for i in range(1):  # three
        a = b = c['side'] = 'effect'
        four()


def four(a=123, b='234', c={'3': [4, '5']}):
    for i in range(1):  # four
        a = b = c['side'] = 'effect'
        five()


def five(a=123, b='234', c={'3': [4, '5']}):
    six()
    six()
    six()
    a = b = c['side'] = in_five = 'effect'
    for i in range(1):  # five
        return i  # five


def six():
    pass


if __name__ == "__main__":
    from hunter import *

    from utils import DebugCallPrinter

    trace(
        Backlog(stack=15, vars=True, action=DebugCallPrinter(' [' 'backlog' ']'), function='five').filter(~Q(function='six')),
        action=DebugCallPrinter
    )
    one()
    one()  # make sure Backlog is reusable (doesn't have storage side-effects)
    stop()

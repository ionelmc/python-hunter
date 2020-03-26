from __future__ import print_function

import os
import sys
import hunter
# hunter.trace(hunter.Backlog(source_has='four', kind='call', size=2, stack_depth=10))#.filter(source_has='five'))
# hunter.trace(hunter.Backlog(fullsource_has='return i', size=5))
# hunter.trace(
        #hunter.Backlog(fullsource_has='return i', size=5).filter(~hunter.Q(fullsource_has="five")),
        # hunter.Q(fullsource_has='return i') | hunter.Q(fullsource_contains='three') | hunter.Q(fullsource_contains='four'), kind_in=['call', 'line']
    # )


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

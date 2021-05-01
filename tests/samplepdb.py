import os
import sys

import hunter


def on_postmortem():
    print('Raising stuff ...', os.getpid())
    try:
        raise Exception("BOOM!")
    except Exception:
        pdb.pm()


def on_settrace():
    print('Doing stuff ...', os.getpid())
    pdb.set_trace()


def one():
    for i in range(2):  # one
        two()


def two():
    for i in range(2):  # two
        three()


def three():
    print('Debugme!')


def on_debugger():
    one()


if __name__ == '__main__':
    if sys.argv[1] == 'pdb':
        import pdb
    elif sys.argv[1] == 'ipdb':
        import ipdb as pdb

    if sys.argv[2] == 'debugger':
        with hunter.trace(source__has='Debugme!', action=hunter.Debugger(lambda: pdb)):
            on_debugger()
    else:
        with hunter.trace():
            if sys.argv[2] == 'postmortem':
                on_postmortem()
            elif sys.argv[2] == 'settrace':
                on_settrace()
            else:
                raise RuntimeError(sys.argv)

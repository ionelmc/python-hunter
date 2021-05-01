import os
import sys
import time


def stuff():
    print('Doing stuff ...', os.getpid())
    time.sleep(1)


if __name__ == '__main__':
    if sys.argv[1] == 'manhole':
        from hunter import remote

        remote.install()

    while True:
        stuff()

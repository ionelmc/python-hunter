import sys
import time


def stuff():
    print('Doing stuff ...')
    time.sleep(1)


if __name__ == '__main__':
    if sys.argv[1] == 'manhole':
        from hunter import remote

        remote.install()

    while True:
        stuff()

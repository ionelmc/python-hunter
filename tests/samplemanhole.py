import os
import time


def stuff():
    print('Doing stuff ...', os.getpid())
    time.sleep(1)


if __name__ == '__main__':
    from hunter import remote

    remote.install()

    while True:
        stuff()

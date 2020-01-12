import logging

logger = logging.getLogger(__name__)


def error():
    raise RuntimeError()


def silenced1():
    try:
        error()
    except Exception:
        pass


def silenced2():
    try:
        error()
    except Exception as exc:
        print(exc)
        for i in range(25):
            print(i)
    return 'x'


def silenced3():
    try:
        error()
    finally:
        return "mwhahaha"


def silenced4():
    try:
        error()
    except Exception as exc:
        logger.info(repr(exc))


def notsilenced():
    try:
        error()
    except Exception as exc:
        raise ValueError(exc)


silenced1()
print("Done silenced1")
silenced2()
print("Done silenced2")
silenced3()
print("Done silenced3")
silenced4()
print("Done silenced4")

try:
    notsilenced()
except ValueError:
    print("Done not silenced")

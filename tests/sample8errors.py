import logging

logger = logging.getLogger(__name__)


def error():
    raise RuntimeError()


def log(msg):
    print(msg)


def silenced1():
    try:
        error()
    except Exception:
        pass


def silenced2():
    try:
        error()
    except Exception as exc:
        log(exc)
        for i in range(200):
            log(i)
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

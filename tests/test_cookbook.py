import collections
import contextlib
import functools
import opcode
import os
import sys
from logging import getLogger

import aspectlib
import pytest

import hunter
from hunter import CallPrinter
from hunter import CodePrinter
from hunter import VarsSnooper

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

logger = getLogger(__name__)

pytest_plugins = 'pytester',


def nothin(x):
    return x


def bar():
    baz()


@nothin
@nothin
@nothin
@nothin
def baz():
    for i in range(10):
        os.path.join('a', str(i))
    foo = 1


def brief_probe(qualname, *actions, **kwargs):
    return aspectlib.weave(qualname, functools.partial(hunter.wrap, actions=actions, **kwargs))


def fast_probe(qualname, *actions, **filters):
    def tracing_decorator(func):
        @functools.wraps(func)
        def tracing_wrapper(*args, **kwargs):
            # create the Tracer manually to avoid spending time in likely useless things like:
            # - loading PYTHONHUNTERCONFIG
            # - setting up the clear_env_var or thread_support options
            # - atexit cleanup registration
            with hunter.Tracer().trace(hunter.When(hunter.Query(**filters), *actions)):
                return func(*args, **kwargs)

        return tracing_wrapper

    return aspectlib.weave(qualname, tracing_decorator)  # this does the monkeypatch


@contextlib.contextmanager
def no_probe(*args, **kwargs):
    yield


@pytest.mark.parametrize('impl', [fast_probe, brief_probe, no_probe])
def test_probe(impl, benchmark):
    with impl('%s.baz' % __name__, hunter.VarsPrinter('foo', stream=open(os.devnull, 'w')), kind="return", depth=0):
        benchmark(bar)

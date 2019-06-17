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
        baz()


def notsilenced():
    try:
        error()
    except Exception as exc:
        raise ValueError(exc)


RETURN_VALUE = opcode.opmap['RETURN_VALUE']


class DumpExceptions(hunter.CodePrinter):
    events = ()
    depth = 0
    count = 0
    exc = None

    def __init__(self, max_count=10, **kwargs):
        self.max_count = max_count
        self.backlog = collections.deque(maxlen=5)
        super(DumpExceptions, self).__init__(**kwargs)

    def __call__(self, event):
        self.count += 1
        if event.kind == 'exception':  # something interesting happened ;)
            self.events = list(self.backlog)
            self.events.append(event.detach(self.try_repr))
            self.exc = self.try_repr(event.arg[1])
            self.depth = event.depth
            self.count = 0
        elif self.events:
            if event.depth > self.depth:  # too many details
                return
            elif event.depth < self.depth and event.kind == 'return':  # stop if function returned
                op = event.code.co_code[event.frame.f_lasti]
                op = op if isinstance(op, int) else ord(op)
                if op == RETURN_VALUE:
                    self.output("{BRIGHT}{fore(BLUE)}{} tracing {} on {}{RESET}\n",
                                ">" * 46, event.function, self.exc)
                    for event in self.events:
                        super(DumpExceptions, self).__call__(event)
                    if self.count > 10:
                        self.output("{BRIGHT}{fore(BLACK)}{} too many lines{RESET}\n",
                                    "-" * 46)
                    else:
                        self.output("{BRIGHT}{fore(BLACK)}{} function exit{RESET}\n",
                                    "-" * 46)
                self.events = []
                self.exc = None
            elif self.count < self.max_count:
                self.events.append(event.detach(self.try_repr))
        else:
            self.backlog.append(event.detach(self.try_repr))


def test_dump_exceptions(LineMatcher):
    stream = StringIO()
    with hunter.trace(stdlib=False, action=DumpExceptions(stream=stream)):
        silenced1()
        silenced2()
        silenced3()
        silenced4()

        print("Done silenced")
        try:
            notsilenced()
            print("Done not silenced")
        except ValueError:
            pass
    lm = LineMatcher(stream.getvalue().splitlines())
    lm.fnmatch_lines([
        '*>>>>>>>>>>>>>>>>>>>>>> tracing silenced1 on RuntimeError()',
        '*test_cookbook.py:***   exception         error()',
        '*                 ***   ...       exception value: *RuntimeError*',
        '*test_cookbook.py:***   line          except Exception:',
        '*test_cookbook.py:***   line              pass',
        '*---------------------- function exit',
        '*>>>>>>>>>>>>>>>>>>>>>> tracing silenced2 on RuntimeError()',
        '*test_cookbook.py:***   exception         error()',
        '*                       ...       exception value: *RuntimeError*',
        '*test_cookbook.py:***   line          except Exception as exc:',
        '*test_cookbook.py:***   line              print(exc)',
        '*---------------------- too many lines',
        '*>>>>>>>>>>>>>>>>>>>>>> tracing silenced3 on RuntimeError()',
        '*test_cookbook.py:***   exception         error()',
        '*                       ...       exception value: *RuntimeError*',
        '*test_cookbook.py:***   line              return "mwhahaha"',
        '*---------------------- function exit',
        '*>>>>>>>>>>>>>>>>>>>>>> tracing silenced4 on RuntimeError()',
        '*test_cookbook.py:***   exception         error()',
        '*                       ...       exception value: *RuntimeError*',
        '*test_cookbook.py:***   line          except Exception as exc:',
        '*test_cookbook.py:***   line              logger.info(repr(exc))',
        '*---------------------- too many lines',
    ])


def test_examples():
    print("""
    CodePrinter
    """)
    with hunter.trace(stdlib=False, actions=[CodePrinter, VarsSnooper]):
        os.path.join(*map(str, range(10)))

    print("""
    CallPrinter
    """)
    with hunter.trace(stdlib=False, actions=[CallPrinter, VarsSnooper]):
        os.path.join(*map(str, range(10)))

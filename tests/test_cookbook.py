import contextlib
import functools
import os
from logging import getLogger
from time import time

import aspectlib
import pytest

import hunter
from hunter.actions import RETURN_VALUE
from hunter.actions import ColorStreamAction

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
    with impl('%s.baz' % __name__, hunter.VarsPrinter('foo', stream=open(os.devnull, 'w')), kind='return', depth=0):
        benchmark(bar)


class ProfileAction(ColorStreamAction):
    # using ColorStreamAction brings this more in line with the other actions
    # (stream option, coloring and such, see the other examples for colors)
    def __init__(self, **kwargs):
        self.timings = {}
        super(ProfileAction, self).__init__(**kwargs)

    def __call__(self, event):
        current_time = time()
        # include event.builtin in the id so we don't have problems
        # with Python reusing frame objects from the previous call for builtin calls
        frame_id = id(event.frame), str(event.builtin)

        if event.kind == 'call':
            self.timings[frame_id] = current_time, None
        elif frame_id in self.timings:
            start_time, exception = self.timings.pop(frame_id)

            # try to find a complete function name for display
            function_object = event.function_object
            if event.builtin:
                function = '<builtin>.{}'.format(event.arg.__name__)
            elif function_object:
                if hasattr(function_object, '__qualname__'):
                    function = '{}.{}'.format(
                        function_object.__module__, function_object.__qualname__
                    )
                else:
                    function = '{}.{}'.format(
                        function_object.__module__,
                        function_object.__name__
                    )
            else:
                function = event.function

            if event.kind == 'exception':
                # store the exception
                # (there will be a followup 'return' event in which we deal with it)
                self.timings[frame_id] = start_time, event.arg
            elif event.kind == 'return':
                delta = current_time - start_time
                if event.instruction == RETURN_VALUE:
                    # exception was discarded
                    self.output(
                        '{fore(BLUE)}{} returned: {}. Duration: {:.4f}s{RESET}\n',
                        function, event.arg, delta
                    )
                else:
                    self.output(
                        '{fore(RED)}{} raised exception: {}. Duration: {:.4f}s{RESET}\n',
                        function, exception, delta
                    )


@pytest.mark.parametrize('options', [
    {'kind__in': ['call', 'return', 'exception']},
    {'profile': True}
])
def test_profile(LineMatcher, options):
    stream = StringIO()
    with hunter.trace(action=ProfileAction(stream=stream), **options):
        from sample8errors import notsilenced
        from sample8errors import silenced1
        from sample8errors import silenced3
        from sample8errors import silenced4

        silenced1()
        print('Done silenced1')
        silenced3()
        print('Done silenced3')
        silenced4()
        print('Done silenced4')

        try:
            notsilenced()
        except ValueError:
            print('Done not silenced')

    lm = LineMatcher(stream.getvalue().splitlines())
    if 'profile' in options:
        lm.fnmatch_lines([
            "sample8errors.error raised exception: None. Duration: ?.????s",
            "sample8errors.silenced1 returned: None. Duration: ?.????s",

            "sample8errors.error raised exception: None. Duration: ?.????s",
            "sample8errors.silenced3 returned: mwhahaha. Duration: ?.????s",

            "sample8errors.error raised exception: None. Duration: ?.????s",
            "<builtin>.repr raised exception: None. Duration: ?.????s",
            "sample8errors.silenced4 returned: None. Duration: ?.????s",

            "sample8errors.error raised exception: None. Duration: ?.????s",
            "sample8errors.notsilenced raised exception: None. Duration: ?.????s",
        ])
    else:
        lm.fnmatch_lines([
            "sample8errors.error raised exception: (*RuntimeError*, *). Duration: ?.????s",
            "sample8errors.silenced1 returned: None. Duration: ?.????s",

            "sample8errors.error raised exception: (*RuntimeError*, *). Duration: ?.????s",
            "sample8errors.silenced3 returned: mwhahaha. Duration: ?.????s",

            "sample8errors.error raised exception: (*RuntimeError*, *). Duration: ?.????s",
            "sample8errors.silenced4 returned: None. Duration: ?.????s",

            "sample8errors.error raised exception: (*RuntimeError*, *). Duration: ?.????s",
            "sample8errors.notsilenced raised exception: (*ValueError(RuntimeError*, *). Duration: ?.????s",
        ])

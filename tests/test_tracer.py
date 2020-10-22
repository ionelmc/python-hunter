from __future__ import print_function

import functools
import os
import platform
import sys
import threading
from pprint import pprint

import pytest

import hunter
from hunter import And
from hunter import Backlog
from hunter import CallPrinter
from hunter import CodePrinter
from hunter import Debugger
from hunter import ErrorSnooper
from hunter import From
from hunter import Q
from hunter import VarsPrinter
from hunter import VarsSnooper
from hunter import When
from hunter.actions import StackPrinter

from utils import DebugCallPrinter

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO


if hunter.Tracer.__module__ == 'hunter.tracer':
    class EvilFrame(object):
        f_back = None
        f_globals = {}
        f_locals = {}
        f_lineno = 0

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class EvilTracer(object):
        is_pure = True

        def __init__(self, *args, **kwargs):
            self._calls = []
            threading_support = kwargs.pop('threading_support', False)
            clear_env_var = kwargs.pop('clear_env_var', False)
            self.handler = hunter._prepare_predicate(*args, **kwargs)
            self._tracer = hunter.trace(self._append, threading_support=threading_support, clear_env_var=clear_env_var)

        def _append(self, event):
            detached_event = event.detach(lambda obj: obj)
            detached_event.detached = False
            detached_event.frame = EvilFrame(
                f_globals=event.frame.f_globals,
                f_locals=event.frame.f_locals,

                f_back=event.frame.f_back,
                f_lasti=event.frame.f_lasti,
                f_code=event.code
            )
            self._calls.append(detached_event)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self._tracer.stop()
            predicate = self.handler
            for call in self._calls:
                predicate(call)
else:
    from eviltracer import EvilTracer


trace = EvilTracer

pytest_plugins = 'pytester',

PY3 = sys.version_info[0] == 3


def test_mix_predicates_with_callables():
    hunter._prepare_predicate(Q(module=1) | Q(lambda: 2))
    hunter._prepare_predicate(Q(lambda: 2) | Q(module=1))
    hunter._prepare_predicate(Q(module=1) & Q(lambda: 2))
    hunter._prepare_predicate(Q(lambda: 2) & Q(module=1))

    hunter._prepare_predicate(Q(module=1) | (lambda: 2))
    hunter._prepare_predicate((lambda: 2) | Q(module=1))
    hunter._prepare_predicate(Q(module=1) & (lambda: 2))
    hunter._prepare_predicate((lambda: 2) & Q(module=1))


def test_predicate_reverse_and_or():
    class Foobar(object):
        def __str__(self):
            return 'Foobar'

        __repr__ = __str__

        def __call__(self, *args, **kwargs):
            pass

    foobar = Foobar()

    assert str(foobar & Q(module=1)) == 'And(Foobar, Query(module=1))'
    assert str(foobar | Q(module=1)) == 'Or(Foobar, Query(module=1))'
    assert str(foobar & (Q(module=1) | Q(module=2))) == 'And(Foobar, Or(Query(module=1), Query(module=2)))'
    assert str(foobar | (Q(module=1) | Q(module=2))) == 'Or(Foobar, Query(module=1), Query(module=2))'
    assert str(foobar & (Q(module=1) & Q(module=2))) == 'And(Foobar, Query(module=1), Query(module=2))'
    assert str(foobar | (Q(module=1) & Q(module=2))) == 'Or(Foobar, And(Query(module=1), Query(module=2)))'
    assert str(foobar & ~Q(module=1)) == 'And(Foobar, Not(Query(module=1)))'
    assert str(foobar | ~Q(module=1)) == 'Or(Foobar, Not(Query(module=1)))'
    assert str(foobar & Q(module=1, action=foobar)) == 'And(Foobar, When(Query(module=1), Foobar))'
    assert str(foobar | Q(module=1, action=foobar)) == 'Or(Foobar, When(Query(module=1), Foobar))'
    assert str(foobar & ~Q(module=1, action=foobar)) == 'And(Foobar, Not(When(Query(module=1), Foobar)))'
    assert str(foobar | ~Q(module=1, action=foobar)) == 'Or(Foobar, Not(When(Query(module=1), Foobar)))'
    assert str(foobar & From(module=1, depth=2)) == 'And(Foobar, From(Query(module=1), Query(depth=2), watermark=0))'
    assert str(foobar | From(module=1, depth=2)) == 'Or(Foobar, From(Query(module=1), Query(depth=2), watermark=0))'
    assert str(foobar & ~From(module=1, depth=2)) == 'And(Foobar, Not(From(Query(module=1), Query(depth=2), watermark=0)))'
    assert str(foobar | ~From(module=1, depth=2)) == 'Or(Foobar, Not(From(Query(module=1), Query(depth=2), watermark=0)))'
    assert str(From(module=1, depth=2) & foobar) == 'And(From(Query(module=1), Query(depth=2), watermark=0), Foobar)'
    assert str(From(module=1, depth=2) | foobar) == 'Or(From(Query(module=1), Query(depth=2), watermark=0), Foobar)'
    assert str(foobar & Backlog(module=1)).startswith('And(Foobar, Backlog(Query(module=1), ')
    assert str(foobar | Backlog(module=1)).startswith('Or(Foobar, Backlog(Query(module=1), ')
    assert str(foobar & ~Backlog(module=1)).startswith('And(Foobar, Backlog(Not(Query(module=1)), ')
    assert str(foobar | ~Backlog(module=1)).startswith('Or(Foobar, Backlog(Not(Query(module=1)), ')
    assert str(Backlog(module=1) & foobar).startswith('And(Backlog(Query(module=1), ')
    assert str(Backlog(module=1) | foobar).startswith('Or(Backlog(Query(module=1), ')
    assert str(Q(module=1) & foobar) == 'And(Query(module=1), Foobar)'
    assert str(Q(module=1) | foobar) == 'Or(Query(module=1), Foobar)'
    assert str(~Q(module=1) & foobar) == 'And(Not(Query(module=1)), Foobar)'
    assert str(~Q(module=1) | foobar) == 'Or(Not(Query(module=1)), Foobar)'
    assert str(Q(module=1, action=foobar) & foobar) == 'And(When(Query(module=1), Foobar), Foobar)'
    assert str(Q(module=1, action=foobar) | foobar) == 'Or(When(Query(module=1), Foobar), Foobar)'
    assert str(~Q(module=1, action=foobar) & foobar) == 'And(Not(When(Query(module=1), Foobar)), Foobar)'
    assert str(~Q(module=1, action=foobar) | foobar) == 'Or(Not(When(Query(module=1), Foobar)), Foobar)'


def test_threading_support(LineMatcher):
    lines = StringIO()
    idents = set()
    names = set()
    started = threading.Event()

    def record(event):
        idents.add(event.threadid)
        names.add(event.threadname)
        return True

    with hunter.trace(record,
                      actions=[CodePrinter(stream=lines), VarsPrinter('a', stream=lines), CallPrinter(stream=lines)],
                      threading_support=True):
        def foo(a=1):
            started.set()
            print(a)

        def main():
            foo()

        t = threading.Thread(target=foo)
        t.start()
        started.wait(10)
        main()

    lm = LineMatcher(lines.getvalue().splitlines())
    assert idents - {t.ident} == {None}
    assert 'MainThread' in names
    assert any(name.startswith('Thread-') for name in names)
    lm.fnmatch_lines_random([
        'Thread-*   *test_tracer.py:*   call              def foo(a=1):',
        'Thread-*   *test_tracer.py:*   call      [[]a => 1[]]',
        'Thread-*   *test_tracer.py:*   call         => foo(a=1)',
        'Thread-*   *test_tracer.py:*   call      [[]a => 1[]]',
        'MainThread *test_tracer.py:*   call              def foo(a=1):',
        'MainThread *test_tracer.py:*   call      [[]a => 1[]]',
        'MainThread *test_tracer.py:*   call         => foo(a=1)',
        'MainThread *test_tracer.py:*   call      [[]a => 1[]]',
    ])


@pytest.mark.parametrize('query', [{'threadid': None}, {'threadname': 'MainThread'}])
def test_thread_filtering(LineMatcher, query):
    lines = StringIO()
    idents = set()
    names = set()
    started = threading.Event()

    def record(event):
        idents.add(event.threadid)
        names.add(event.threadname)
        return True

    with hunter.trace(~Q(**query), record,
                      actions=[CodePrinter(stream=lines), VarsPrinter('a', stream=lines), CallPrinter(stream=lines)],
                      threading_support=True):
        def foo(a=1):
            started.set()
            print(a)

        def main():
            foo()

        t = threading.Thread(target=foo)
        t.start()
        started.wait(10)
        main()

    lm = LineMatcher(lines.getvalue().splitlines())
    print(lines.getvalue())
    assert None not in idents
    assert 'MainThread' not in names
    pprint(lm.lines)
    lm.fnmatch_lines_random([
        'Thread-*   *test_tracer.py:*   call              def foo(a=1):',
        'Thread-*   *test_tracer.py:*   call      [[]a => 1[]]',
        'Thread-*   *test_tracer.py:*   call         => foo(a=1)',
        'Thread-*   *test_tracer.py:*   call      [[]a => 1[]]',
    ])


def test_tracing_printing_failures(LineMatcher):
    lines = StringIO()
    with trace(actions=[CodePrinter(stream=lines, repr_func=repr), VarsPrinter('x', stream=lines, repr_func=repr)]):
        class Bad(object):
            __slots__ = []

            def __repr__(self):
                raise RuntimeError("I'm a bad class!")

        def a():
            x = Bad()
            return x

        def b():
            x = Bad()
            raise Exception(x)

        a()
        try:
            b()
        except Exception as exc:
            pass
    lm = LineMatcher(lines.getvalue().splitlines())
    print(lines.getvalue())
    lm.fnmatch_lines([
        """*tests*test_*.py:* call              class Bad(object):""",
        """*tests*test_*.py:* line              class Bad(object):""",
        """*tests*test_*.py:* line                  def __repr__(self):""",
        """*tests*test_*.py:* return                def __repr__(self):""",
        """* ...       return value: *""",
        """*tests*test_*.py:* call              def a():""",
        """*tests*test_*.py:* line                  x = Bad()""",
        """*tests*test_*.py:* line                  return x""",
        """*tests*test_*.py:* line      [[]x => !!! FAILED REPR: RuntimeError("I'm a bad class!"*)[]]""",
        """*tests*test_*.py:* return                return x""",
        """* ...       return value: !!! FAILED REPR: RuntimeError("I'm a bad class!"*)""",
        """*tests*test_*.py:* call              def b():""",
        """*tests*test_*.py:* line                  x = Bad()""",
        """*tests*test_*.py:* line                  raise Exception(x)""",
        """*tests*test_*.py:* line      [[]x => !!! FAILED REPR: RuntimeError("I'm a bad class!"*)[]]""",
        """*tests*test_*.py:* exception             raise Exception(x)""",
        """* ...       exception value: !!! FAILED REPR: RuntimeError("I'm a bad class!"*)""",
        """*tests*test_*.py:* return                raise Exception(x)""",
        """* ...       return value: None""",
    ])


def test_tracing_vars(LineMatcher):
    lines = StringIO()
    with hunter.trace(actions=[VarsPrinter('b', stream=lines), CodePrinter(stream=lines)]):
        def a():
            b = 1
            b = 2
            return 1

        b = a()
        b = 2
        try:
            raise Exception('BOOM!')
        except Exception:
            pass
    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*test_tracer.py* call              def a():",
        "*test_tracer.py* line                  b = 1",
        "*test_tracer.py* line      [[]b => 1[]]",
        "*test_tracer.py* line                  b = 2",
        "*test_tracer.py* line      [[]b => 2[]]",
        "*test_tracer.py* line                  return 1",
        "*test_tracer.py* return    [[]b => 2[]]",
        "*test_tracer.py* return                return 1",
        "*                ...       return value: 1",
    ])


def test_tracing_vars_expressions(LineMatcher):
    lines = StringIO()
    with hunter.trace(actions=[VarsPrinter('Foo.bar', 'vars(Foo)', 'len(range(2))', 'Foo.__dict__["bar"]', stream=lines)]):
        def main():
            class Foo(object):
                bar = 1

        main()
    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines_random([
        '*    [[]Foo.bar => 1[]]',
        '*    [[]vars(Foo) => *[]]',
        '*    [[]len(range(2)) => 2[]]',
        '*    [[]Foo.__dict__[[]"bar"[]] => 1[]]',
    ])


def test_trace_merge():
    with hunter.trace(function='a'):
        with hunter.trace(function='b'):
            with hunter.trace(function='c'):
                assert sys.gettrace().handler == When(Q(function='c'), CallPrinter)
            assert sys.gettrace().handler == When(Q(function='b'), CallPrinter)
        assert sys.gettrace().handler == When(Q(function='a'), CallPrinter)


def test_trace_api_expansion():
    # simple use
    with trace(function='foobar') as t:
        assert t.handler == When(Q(function='foobar'), CallPrinter)

    # 'or' by expression
    with trace(module='foo', function='foobar') as t:
        assert t.handler == When(Q(module='foo', function='foobar'), CallPrinter)

    # pdb.set_trace
    with trace(function='foobar', action=Debugger) as t:
        assert str(t.handler) == str(When(Q(function='foobar'), Debugger))

    # pdb.set_trace on any hits
    with trace(module='foo', function='foobar', action=Debugger) as t:
        assert str(t.handler) == str(When(Q(module='foo', function='foobar'), Debugger))

    # pdb.set_trace when function is foobar, otherwise just print when module is foo
    with trace(Q(function='foobar', action=Debugger), module='foo') as t:
        assert str(t.handler) == str(When(And(
            When(Q(function='foobar'), Debugger),
            Q(module='foo')
        ), CallPrinter))

    # dumping variables from stack
    with trace(Q(function='foobar', action=VarsPrinter('foobar')), module='foo') as t:
        assert str(t.handler) == str(When(And(
            When(Q(function='foobar'), VarsPrinter('foobar')),
            Q(module='foo'),
        ), CallPrinter))

    with trace(Q(function='foobar', action=VarsPrinter('foobar', 'mumbojumbo')), module='foo') as t:
        assert str(t.handler) == str(When(And(
            When(Q(function='foobar'), VarsPrinter('foobar', 'mumbojumbo')),
            Q(module='foo'),
        ), CallPrinter))

    # multiple actions
    with trace(Q(function='foobar', actions=[VarsPrinter('foobar'), Debugger]), module='foo') as t:
        assert str(t.handler) == str(When(And(
            When(Q(function='foobar'), VarsPrinter('foobar'), Debugger),
            Q(module='foo'),
        ), CallPrinter))


def test_locals():
    out = StringIO()
    with hunter.trace(
        lambda event: event.locals.get('node') == 'Foobar',
        module=__name__,
        function='foo',
        action=CodePrinter(stream=out)
    ):
        def foo():
            a = 1
            node = 'Foobar'
            node += 'x'
            a += 2
            return a

        foo()
    assert out.getvalue().endswith("node += 'x'\n")


def test_fullsource_decorator_issue(LineMatcher):
    out = StringIO()
    with trace(kind='call', action=CodePrinter(stream=out)):
        foo = bar = lambda x: x

        @foo
        @bar
        def foo():
            return 1

        foo()

    lm = LineMatcher(out.getvalue().splitlines())
    lm.fnmatch_lines([
        '* call              @foo',
        '*    |              @bar',
        '*    *              def foo():',
    ])


def test_callprinter(LineMatcher):
    out = StringIO()
    with trace(action=CallPrinter(stream=out)):
        foo = bar = lambda x: x

        @foo
        @bar
        def foo():
            return 1

        foo()

    lm = LineMatcher(out.getvalue().splitlines())
    lm.fnmatch_lines([
        '* call      => <lambda>(x=<function *foo at *>)',
        '* line         foo = bar = lambda x: x',
        '* return    <= <lambda>: <function *foo at *>',
        '* call      => <lambda>(x=<function *foo at *>)',
        '* line         foo = bar = lambda x: x',
        '* return    <= <lambda>: <function *foo at *>',
        '* call      => foo()',
        '* line         return 1',
        '* return    <= foo: 1',
    ])


def test_callprinter_indent(LineMatcher):
    from sample6 import bar
    out = StringIO()
    with trace(action=CallPrinter(stream=out)):
        bar()

    lm = LineMatcher(out.getvalue().splitlines())
    lm.fnmatch_lines([
        "*sample6.py:1     call      => bar()",
        "*sample6.py:2     line         foo()",
        "*sample6.py:5     call         => foo()",
        "*sample6.py:6     line            try:",
        "*sample6.py:7     line            asdf()",
        "*sample6.py:16    call            => asdf()",
        "*sample6.py:17    line               raise Exception()",
        "*sample6.py:17    exception        ! asdf: (<*Exception'>, Exception(), <traceback object at *>)",
        "*sample6.py:17    return          <= asdf: None",
        "*sample6.py:7     exception     ! foo: (<*Exception'>, Exception(), <traceback object at *>)",
        "*sample6.py:8     line            except:",
        "*sample6.py:9     line            pass",
        "*sample6.py:10    line            try:",
        "*sample6.py:11    line            asdf()",
        "*sample6.py:16    call            => asdf()",
        "*sample6.py:17    line               raise Exception()",
        "*sample6.py:17    exception        ! asdf: (<*Exception'>, Exception(), <traceback object at *>)",
        "*sample6.py:17    return          <= asdf: None",
        "*sample6.py:11    exception     ! foo: (<*Exception'>, Exception(), <traceback object at *>)",
        "*sample6.py:12    line            except:",
        "*sample6.py:13    line            pass",
        "*sample6.py:13    return       <= foo: None",
        "*sample6.py:2     return    <= bar: None",

    ])


def test_source(LineMatcher):
    calls = []
    with trace(action=lambda event: calls.append(event.source)):
        foo = bar = lambda x: x

        @foo
        @bar
        def foo():
            return 1

        foo()

    lm = LineMatcher(calls)
    lm.fnmatch_lines([
        '        foo = bar = lambda x: x\n',
        '        @foo\n',
        '            return 1\n',
    ])


def test_wraps(LineMatcher):
    calls = []

    @hunter.wrap(action=lambda event: calls.append('%6r calls=%r depth=%r %s' % (event.kind, event.calls, event.depth, event.fullsource)))
    def foo():
        return 1

    foo()
    lm = LineMatcher(calls)
    for line in calls:
        print(repr(line))
    lm.fnmatch_lines([
        "'call' calls=0 depth=0     @hunter.wrap*",
        "'line' calls=1 depth=1         return 1\n",
        "'return' calls=1 depth=0         return 1\n",
    ])
    for call in calls:
        assert 'tracer.stop()' not in call


def test_wraps_local(LineMatcher):
    calls = []

    def bar():
        for i in range(2):
            return 'A'

    @hunter.wrap(local=True, action=lambda event: calls.append(
        '%06s calls=%s depth=%s %s' % (event.kind, event.calls, event.depth, event.fullsource)))
    def foo():
        bar()
        return 1

    foo()
    lm = LineMatcher(calls)
    for line in calls:
        print(repr(line))
    lm.fnmatch_lines([
        '  call calls=0 depth=0     @hunter.wrap*',
        '  line calls=? depth=1         return 1\n',
        'return calls=? depth=0         return 1\n',
    ])
    for call in calls:
        assert 'for i in range(2)' not in call
        assert 'tracer.stop()' not in call


@pytest.mark.skipif('os.environ.get("SETUPPY_CFLAGS") == "-DCYTHON_TRACE=1"')
def test_depth():
    calls = []
    tracer = hunter.trace(action=lambda event: calls.append((event.kind, event.module, event.function, event.depth)))
    try:
        def bar():
            for i in range(2):
                yield i

        def foo():
            gen = bar()
            next(gen)
            while True:
                try:
                    gen.send('foo')
                except StopIteration:
                    break
            list(i for i in range(2))
            x = [i for i in range(2)]

        foo()
    finally:
        tracer.stop()
    pprint(calls)
    assert ('call', __name__, 'bar', 1) in calls
    assert ('return', __name__, 'foo', 0) in calls


def test_source_cython(LineMatcher):
    pytest.importorskip('sample5')
    calls = []
    from sample5 import foo
    with trace(action=lambda event: calls.append(event.source)):
        foo()

    lm = LineMatcher(calls)
    lm.fnmatch_lines([
        'def foo():\n',
        '    return 1\n',
    ])


def test_fullsource(LineMatcher):
    calls = []
    with trace(action=lambda event: calls.append(event.fullsource)):
        foo = bar = lambda x: x

        @foo
        @bar
        def foo():
            return 1

        foo()

    lm = LineMatcher(calls)
    lm.fnmatch_lines([
        '        foo = bar = lambda x: x\n',
        '        @foo\n        @bar\n        def foo():\n',
        '            return 1\n',
    ])


def test_fullsource_cython(LineMatcher):
    pytest.importorskip('sample5')
    calls = []
    from sample5 import foo
    with trace(action=lambda event: calls.append(event.fullsource)):
        foo()

    lm = LineMatcher(calls)
    lm.fnmatch_lines([
        'def foo():\n',
        '    return 1\n',
    ])


def test_custom_action():
    calls = []

    with trace(action=lambda event: calls.append(event.function), kind='return'):
        def foo():
            return 1

        foo()
    assert 'foo' in calls


def test_trace_with_class_actions():
    with trace(CodePrinter):
        def a():
            pass

        a()


def test_proper_backend():
    if os.environ.get('PUREPYTHONHUNTER') or platform.python_implementation() == 'PyPy':
        assert 'hunter.tracer.Tracer' in repr(hunter.Tracer)
        assert hunter.Tracer.__module__ == 'hunter.tracer'
    else:
        assert 'hunter._tracer.Tracer' in repr(hunter.Tracer)
        assert hunter.Tracer.__module__ == 'hunter._tracer'


@pytest.fixture(params=['pure', 'cython'])
def tracer_impl(request):
    if request.param == 'pure':
        Tracer = pytest.importorskip('hunter.tracer').Tracer
    elif request.param == 'cython':
        Tracer = pytest.importorskip('hunter._tracer').Tracer

    if Tracer is not hunter.Tracer:
        pytest.skip("%s is not %s in this environment" % (Tracer, hunter.Tracer))

    return Tracer


def _bulky_func_that_use_stdlib():
    import difflib
    a = list(map(str, range(500)))
    b = list(map(str, range(0, 500, 2)))
    list(difflib.unified_diff(a, b, 'a', 'b'))


def test_perf_filter(tracer_impl, benchmark):
    impl = tracer_impl()

    class Counter(object):
        calls = 0

    def inc(_):
        Counter.calls += 1

    handler = Q(
        Q(module='does-not-exist') | Q(module='does not exist'.split()),
        action=inc
    )

    @benchmark
    def run():
        with impl.trace(handler):
            _bulky_func_that_use_stdlib()

    assert Counter.calls == 0


def test_perf_stdlib(tracer_impl, benchmark):
    t = tracer_impl()

    @benchmark
    def run():
        output = StringIO()
        with t.trace(Q(
            ~Q(module_contains='pytest'),
            ~Q(module_in=(__name__, 'hunter.tracer', 'hunter._tracer')),
            ~Q(filename='<string>'),
            ~Q(filename=''),
            stdlib=False,
            action=CodePrinter(stream=output)
        )):
            _bulky_func_that_use_stdlib()
        return output

    assert run.getvalue() == ''


def test_perf_actions(tracer_impl, benchmark):
    t = tracer_impl()

    @benchmark
    def run():
        output = StringIO()
        with t.trace(Q(
            ~Q(module_in=['re', 'sre', 'sre_parse']) & ~Q(module_startswith='namedtuple') & Q(kind='call'),
            actions=[
                CodePrinter(
                    stream=output
                ),
                VarsPrinter(
                    'line',
                    stream=output
                )
            ]
        )):
            _bulky_func_that_use_stdlib()


def test_clear_env_var(monkeypatch):
    monkeypatch.setitem(os.environ, 'PYTHONHUNTER', '123')
    assert os.environ.get('PYTHONHUNTER') == '123'

    out = StringIO()
    with trace(action=CallPrinter(stream=out), clear_env_var=True):
        assert 'PYTHONHUNTER' not in os.environ

    assert os.environ.get('PYTHONHUNTER') is None


def test_from_predicate(LineMatcher):
    buff = StringIO()
    from sample7 import one
    with trace(From(Q(function='five'), CallPrinter(stream=buff))):
        one()
    output = buff.getvalue()
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "* call      => five()",
        "* line         for i in range(1):  # five",
        "* line         return i",
        "* return    <= five: 0",
    ])
    assert '<= four' not in output
    assert 'three' not in output
    assert 'two' not in output
    assert 'one' not in output


def test_from_predicate_with_subpredicate(LineMatcher):
    buff = StringIO()
    from sample7 import one
    with trace(From(Q(source_has='# two'), Q(depth_lt=1)), action=CallPrinter(stream=buff)):
        one()
    output = buff.getvalue()
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        '* line      for i in range(1):  # two',
        '* line      three()',
        '* call      => three()',
        '* return    <= three: None',
        '* line      for i in range(1):  # two',
    ])
    assert 'five' not in output
    assert 'four' not in output
    assert 'one()' not in output
    assert '# one' not in output
    assert len(lm.lines) == 5


def test_from_predicate_line(LineMatcher):
    buff = StringIO()
    from sample7 import one
    with trace(From(Q(fullsource_has='in_five'), CallPrinter(stream=buff))):
        one()
    output = buff.getvalue()
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "* line *    for i in range(1):  # five",
        "* line *    return i",
    ])
    assert 'four' not in output
    assert 'three' not in output
    assert 'two' not in output
    assert 'one' not in output


def test_from_predicate_no_predicate(LineMatcher):
    buff = StringIO()
    from sample7 import one
    with trace(From(Q(function='five')), action=CallPrinter(stream=buff)):
        one()
    output = buff.getvalue()
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "* call      => five()",
        "* line         for i in range(1):  # five",
        "* line         return i",
        "* return    <= five: 0",
    ])
    assert '<= four' not in output
    assert 'three' not in output
    assert 'two' not in output
    assert 'one' not in output


def test_from_predicate_line_no_predicate(LineMatcher):
    buff = StringIO()
    from sample7 import one
    with trace(From(Q(fullsource_has='in_five')), action=CallPrinter(stream=buff)):
        one()
    output = buff.getvalue()
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "* line *    for i in range(1):  # five",
        "* line *    return i",
    ])
    assert 'four' not in output
    assert 'three' not in output
    assert 'two' not in output
    assert 'one' not in output


# def test_backlog_size_call(LineMatcher):
#     backlog_buff = StringIO()
#     tracer_buff = StringIO()
#     from sample7 import one
#     with trace(
#         Backlog(function='five', size=5, action=CallPrinter(stream=backlog_buff)),
#         action=CallPrinter(stream=tracer_buff)
#     ):
#         one()
#     backlog_output = backlog_buff.getvalue()
#     lm = LineMatcher(backlog_output.splitlines())
#     lm.fnmatch_lines([
#         "* line      for i in range(1):  # three",
#         "* line      four()",
#         "* call      => four()",
#         "* line         for i in range(1):  # four",
#         "* line         five()",
#     ])
#     assert '=> three' not in backlog_output
#     assert '=> five()' not in backlog_output
#     assert 'two' not in backlog_output
#     assert 'one' not in backlog_output
#
#     tracer_output = tracer_buff.getvalue()
#     assert len(tracer_output.splitlines()) == 1
#     assert " call         => five()" in tracer_output
#
#
# def test_backlog_size_line(LineMatcher):
#     buff = StringIO()
#     tracer_buff = StringIO()
#     from sample7 import one
#     with trace(
#         Backlog(fullsource_has='return i', size=5, action=CallPrinter(stream=buff)),
#         action=CallPrinter(stream=tracer_buff)
#     ):
#         one()
#     output = buff.getvalue()
#     lm = LineMatcher(output.splitlines())
#     lm.fnmatch_lines([
#         "* line      for i in range(1):  # four",
#         "* line      five()",
#         "* call      => five()",
#         "* line         in_five = 1",
#         "* line         for i in range(1):  # five",
#     ])
#
#     assert 'four' not in output
#
#     tracer_output = tracer_buff.getvalue()
#     assert len(tracer_output.splitlines()) == 1
#     assert " line         return i" in tracer_output
#
#
# def test_backlog_size_call_filter(LineMatcher):
#     buff = StringIO()
#     tracer_buff = StringIO()
#     from sample7 import one
#     with trace(
#         Backlog(function='five', size=5, action=CallPrinter(stream=buff)).filter(~Q(fullsource_has='four')),
#         action=CallPrinter(stream=tracer_buff)
#     ):
#         one()
#     output = buff.getvalue()
#     lm = LineMatcher(output.splitlines())
#     lm.fnmatch_lines([
#         "* line      for i in range(1):  # two",
#         "* line      three()",
#         "* call      => three()",
#         "* line         for i in range(1):  # three",
#         "* line         five()",
#     ])
#     assert "four" not in output
#
#     tracer_output = tracer_buff.getvalue()
#     assert len(tracer_output.splitlines()) == 1
#     assert " call         => five()" in tracer_buff.getvalue()
#
#
# def test_backlog_size_predicate_line_filter(LineMatcher):
#     buff = StringIO()
#     tracer_buff = StringIO()
#     from sample7 import one
#     with trace(
#         Backlog(fullsource_has='return i', size=5, action=CallPrinter(stream=buff)).filter(~Q(fullsource_has="five")),
#         action=CallPrinter(stream=tracer_buff)
#     ):
#         one()
#     output = buff.getvalue()
#     lm = LineMatcher(output.splitlines())
#     lm.fnmatch_lines([
#         "* call      => three()",
#         "* line         for i in range(1):  # three",
#         "* line         four()",
#         "* call         => four()",
#         "* line            for i in range(1):  # four",
#     ])
#
#     assert "five" not in output
#
#     tracer_output = tracer_buff.getvalue()
#     assert len(tracer_output.splitlines()) == 1
#     assert " line            return i" in tracer_output
#
#
# def test_backlog_size_first_line_match(LineMatcher):
#     buff = StringIO()
#     tracer_buff = StringIO()
#     from sample7 import one
#     with trace(Backlog(fullsource_has='one', module_rx='sample7', size=100, action=CallPrinter(stream=buff)).filter(fullsource_has='one'), action=CallPrinter(stream=tracer_buff)):
#         one()
#     output = buff.getvalue()
#     assert not output


def decorator(func):
    @functools.wraps(func)
    def wrapper(*a, **k):
        return func(*a, **k)

    return wrapper


def gf(_):
    pass


@decorator
def dgf(_):
    pass


class Old:
    @staticmethod
    def old_sm(_):
        pass

    @classmethod
    def old_cm(cls, _):
        pass

    def old_m(self, _):
        pass


class Desc(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func


class New(object):
    @staticmethod
    def new_sm(_):
        pass

    @classmethod
    def new_cm(cls, _):
        pass

    def new_m(self, _):
        pass

    new_dm = Desc(gf)
    new_ddm = Desc(dgf)


def test_function_object(LineMatcher):
    def lf(_):
        pass

    @decorator
    def dlf(_):
        pass

    class Local(object):
        @staticmethod
        def local_sm(_):
            pass

        @classmethod
        def local_cm(cls, _):
            pass

        def local_m(self, _):
            pass

        local_dm = Desc(lf)
        local_ddm = Desc(dlf)
        global_dm = Desc(gf)
        global_ddm = Desc(dgf)

    buff = StringIO()
    with trace(actions=[
        hunter.CallPrinter(stream=buff),
        lambda event: buff.write(
            "{0.function}({1})|{2}|{0.kind}\n".format(
                event,
                event.locals.get('_'),
                getattr(event.function_object, '__name__', 'missing')))
    ]):
        gf(1)
        dgf(2)
        lf(3)
        dlf(4)
        Old.old_sm(5)
        Old.old_cm(6)
        Old().old_sm(7)
        Old().old_cm(8)
        Old().old_m(9)
        New.new_sm(10)
        New.new_cm(11)
        New().new_sm(12)
        New().new_cm(13)
        New().new_m(14)
        New().new_dm(15)
        New().new_ddm(16)
        Local.local_sm(17)
        Local.local_cm(18)
        Local().local_sm(19)
        Local().local_cm(20)
        Local().local_m(21)
        Local().local_dm(22)
        Local().local_ddm(23)
        Local().global_dm(24)
        Local().global_ddm(25)

    output = buff.getvalue()
    print(output)
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "gf(1)|gf|call",
        "dgf(2)|{}|call".format('dgf' if PY3 else 'missing'),
        "lf(3)|missing|call",
        "dlf(4)|missing|call",
        "old_sm(5)|{}|call".format('old_sm' if PY3 else 'missing'),
        "old_cm(6)|old_cm|call",
        "old_sm(7)|{}|call".format('old_sm' if PY3 else 'missing'),
        "old_cm(8)|old_cm|call",
        "old_m(9)|old_m|call",
        "new_sm(10)|new_sm|call",
        "new_cm(11)|new_cm|call",
        "new_sm(12)|new_sm|call",
        "new_cm(13)|new_cm|call",
        "new_m(14)|new_m|call",
        "gf(15)|gf|call",
        "dgf(16)|{}|call".format('dgf' if PY3 else 'missing'),
        "local_sm(17)|missing|call",
        "local_cm(18)|local_cm|call",
        "local_sm(19)|missing|call",
        "local_cm(20)|local_cm|call",
        "local_m(21)|local_m|call",
        "lf(22)|missing|call",
        "dlf(23)|missing|call",
        "gf(24)|gf|call",
        "dgf(25)|{}|call".format('dgf' if PY3 else 'missing'),
    ])


def test_tracing_bare(LineMatcher):
    lines = StringIO()
    with trace(CodePrinter(stream=lines)):
        def a():
            return 1

        b = a()
        b = 2
        try:
            raise Exception('BOOM!')
        except Exception:
            pass
    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*test_*.py* call              def a():",
        "*test_*.py* line                  return 1",
        "*test_*.py* return                return 1",
        "* ...       return value: 1",
    ])


@pytest.mark.skipif("not os.environ.get('PUREPYTHONHUNTER')")
def test_debugger(LineMatcher):
    out = StringIO()
    calls = []

    class FakePDB:
        def __init__(self, foobar=1):
            calls.append(foobar)

        def set_trace(self, frame):
            calls.append(frame.f_code.co_name)

    with trace(
        lambda event: event.locals.get('node') == 'Foobar',
        module=__name__,
        function='foo',
        actions=[CodePrinter,
                 VarsPrinter('a', 'node', 'foo', 'test_debugger', stream=out),
                 Debugger(klass=FakePDB, foobar=2)]
    ):
        def foo():
            a = 1
            node = 'Foobar'
            node += 'x'
            a += 2
            return a

        foo()
    print(out.getvalue())
    assert calls == [2, 'foo']
    lm = LineMatcher(out.getvalue().splitlines())
    pprint(lm.lines)
    lm.fnmatch_lines_random([
        "*      [[]test_debugger => <function test_debugger at *[]]",
        "*      [[]node => *Foobar*[]]",
        "*      [[]a => 1[]]",
    ])


def test_varssnooper(LineMatcher):
    lines = StringIO()
    snooper = VarsSnooper(stream=lines)

    def a():
        foo = bar = b = 1
        b = 2
        foo = 3
        foo = bar = 4
        return b

    with trace(function='a', actions=[snooper, CodePrinter(stream=lines)]):
        a()

    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*test_*.py*  line              foo = bar = b = 1",
        "*test_*.py*  line      [[]b := 1[]]",
        "*         *  ...       [[]bar := 1[]]",
        "*         *  ...       [[]foo := 1[]]",
        "*test_*.py*  line              b = 2",
        "*test_*.py*  line      [[]b : 1 => 2[]]",
        "*test_*.py*  line              foo = 3",
        "*test_*.py*  line      [[]foo : 1 => 3[]]",
        "*test_*.py*  line              foo = bar = 4",
        "*test_*.py*  line      [[]bar : 1 => 4[]]",
        "*         *  ...       [[]foo : 3 => 4[]]",
        "*test_*.py*  line              return b",
        "*test_*.py*  return            return b",
        "*         *  ...       return value: 2",
    ])
    assert snooper.stored_reprs == {}


@pytest.mark.skipif("not os.environ.get('PUREPYTHONHUNTER')")
def test_errorsnooper(LineMatcher):
    lines = StringIO()
    snooper = ErrorSnooper(stream=lines, max_backlog=50, max_events=100)

    def a():
        from sample8errors import notsilenced
        from sample8errors import silenced1
        from sample8errors import silenced2
        from sample8errors import silenced3
        from sample8errors import silenced4

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

    with trace(actions=[snooper]):
        a()

    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced1 on (*RuntimeError*)",
        "*test_*.py:*  line              silenced1()",
        "*sample8errors.py:14    call      def silenced1():",
        "*sample8errors.py:15    line          try:",
        "*sample8errors.py:16    line              error()",
        "*sample8errors.py:6     call      def error():",
        "*sample8errors.py:7     line          raise RuntimeError()",
        "*sample8errors.py:7     exception     raise RuntimeError()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:7     return        raise RuntimeError()",
        "*                       ...       return value: None",
        "*sample8errors.py:16    exception         error()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:17    line          except Exception:",
        "*sample8errors.py:18    line              pass",
        "*sample8errors.py:18    return            pass",
        "*                       ...       return value: None",
        "*---------------------- function exit",

        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced2 on (*RuntimeError*)",
        '*test_*.py:*  line              print("Done silenced1")',
        "*test_*.py:*  line              silenced2()",
        "*sample8errors.py:21    call      def silenced2():",
        "*sample8errors.py:22    line          try:",
        "*sample8errors.py:23    line              error()",
        "*sample8errors.py:6     call      def error():",
        "*sample8errors.py:7     line          raise RuntimeError()",
        "*sample8errors.py:7     exception     raise RuntimeError()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:7     return        raise RuntimeError()",
        "*                       ...       return value: None",
        "*sample8errors.py:23    exception         error()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:24    line          except Exception as exc:",
        "*sample8errors.py:25    line              log(exc)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*sample8errors.py:27    line                  log(i)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*sample8errors.py:27    line                  log(i)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*sample8errors.py:27    line                  log(i)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*---------------------- too many lines",

        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced3 on (*RuntimeError*)",
        '*test_*.py:*  line              print("Done silenced2")',
        "*test_*.py:*  line              silenced3()",
        "*sample8errors.py:31    call      def silenced3():",
        "*sample8errors.py:32    line          try:",
        "*sample8errors.py:33    line              error()",
        "*sample8errors.py:6     call      def error():",
        "*sample8errors.py:7     line          raise RuntimeError()",
        "*sample8errors.py:7     exception     raise RuntimeError()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:7     return        raise RuntimeError()",
        "*                       ...       return value: None",
        "*sample8errors.py:33    exception         error()",
        "*                       ...       exception value: (*RuntimeError*)",
        '*sample8errors.py:35    line              return "mwhahaha"',
        '*sample8errors.py:35    return            return "mwhahaha"',
        "*                       ...       return value: 'mwhahaha'",
        "*---------------------- function exit",

        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced4 on (*RuntimeError*)",
        '*test_*.py:*  line              print("Done silenced3")',
        "*test_*.py:*  line              silenced4()",
        "*sample8errors.py:38    call      def silenced4():",
        "*sample8errors.py:39    line          try:",
        "*sample8errors.py:40    line              error()",
        "*sample8errors.py:6     call      def error():",
        "*sample8errors.py:7     line          raise RuntimeError()",
        "*sample8errors.py:7     exception     raise RuntimeError()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:7     return        raise RuntimeError()",
        "*                       ...       return value: None",
        "*sample8errors.py:40    exception         error()",
        "*                       ...       exception value: (*RuntimeError*)",
        "*sample8errors.py:41    line          except Exception as exc:",
        "*sample8errors.py:42    line              logger.info(repr(exc))",
        "*__init__.py:*  call          def info(self, msg, *args, **kwargs):",
        "*sample8errors.py:42    return            logger.info(repr(exc))",
        "*                       ...       return value: None",
        "*---------------------- function exit",
    ])


@pytest.mark.skipif("not os.environ.get('PUREPYTHONHUNTER')")
def test_errorsnooper_fastmode(LineMatcher):
    lines = StringIO()
    snooper = ErrorSnooper(stream=lines, max_backlog=0, max_events=100)

    def a():
        from sample8errors import notsilenced
        from sample8errors import silenced1
        from sample8errors import silenced2
        from sample8errors import silenced3
        from sample8errors import silenced4

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

    with trace(actions=[snooper]):
        a()

    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced1 on (*RuntimeError*)",
        "*sample8errors.py:17    line          except Exception:",
        "*sample8errors.py:18    line              pass",
        "*sample8errors.py:18    return            pass",
        "*                       ...       return value: None",
        "*---------------------- function exit",

        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced2 on (*RuntimeError*)",
        "*sample8errors.py:24    line          except Exception as exc:",
        "*sample8errors.py:25    line              log(exc)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*sample8errors.py:27    line                  log(i)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*sample8errors.py:27    line                  log(i)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*sample8errors.py:27    line                  log(i)",
        "*sample8errors.py:10    call      def log(msg):",
        "*sample8errors.py:11    return        print(msg)",
        "*                       ...       return value: None",
        "*sample8errors.py:26    line              for i in range(*):",
        "*---------------------- too many lines",

        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced3 on (*RuntimeError*)",
        '*sample8errors.py:35    line              return "mwhahaha"',
        '*sample8errors.py:35    return            return "mwhahaha"',
        "*                       ...       return value: 'mwhahaha'",
        "*---------------------- function exit",

        "*>>>>>>>>>>>>>>>>>>>>>> tracing silenced4 on (*RuntimeError*)",
        "*sample8errors.py:41    line          except Exception as exc:",
        "*sample8errors.py:42    line              logger.info(repr(exc))",
        "*__init__.py:*  call          def info(self, msg, *args, **kwargs):",
        "*sample8errors.py:42    return            logger.info(repr(exc))",
        "*                       ...       return value: None",
        "*---------------------- function exit",
    ])


def test_stack_printer_1(LineMatcher):
    buff = StringIO()
    with trace(Q(function="five", action=StackPrinter(limit=1, stream=buff))):
        from sample7 import one
        one()

    output = buff.getvalue()
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "*sample7.py:??:five <= sample7.py:??:four <= sample7.py:??:three <= sample7.py:??:two <= sample7.py:?:one <= test_tracer.py:????:test_stack_printer*"
    ])


def test_stack_printer_2(LineMatcher):
    buff = StringIO()
    with trace(Q(function="five", action=StackPrinter(limit=2, stream=buff))):
        from sample7 import one
        one()

    output = buff.getvalue()
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "*sample7.py:??:five <= tests/sample7.py:??:four <= tests/sample7.py:??:three <= tests/sample7.py:??:two <= tests/sample7.py:?:one <= tests/test_tracer.py:????:test_stack_printer*"
    ])


@pytest.mark.parametrize('stack', [5, 6, 7], ids="stack={}".format)
@pytest.mark.parametrize('size', [6, 8, 10, 12, 14, 16] + list(range(17, 35)), ids="size={}".format)
@pytest.mark.parametrize('vars', [True, False], ids="vars={}".format)
@pytest.mark.parametrize('filter', [None, ~Q(function='six')], ids="filter={}".format)
@pytest.mark.parametrize('condition', [{'fullsource_has': 'return i'}, {'function': 'five'}], ids=urlencode)
def test_backlog_specific(LineMatcher, size, stack, vars, condition, filter):
    buff = StringIO()
    from sample7args import one
    with trace(
        Backlog(size=size, stack=stack, vars=vars, action=DebugCallPrinter(' [' 'backlog' ']', stream=buff), filter=filter, **condition),
        action=DebugCallPrinter(stream=buff)
    ):
        one()
        one()  # make sure Backlog is reusable (doesn't have storage side-effects)

    output = buff.getvalue()
    # print(re.sub(r'([\[\]])', r'[\1]', output))
    lm = LineMatcher(output.splitlines())
    lm.fnmatch_lines([
        "depth=0 calls=*sample7args.py:*  call      => one(a=*, b=*, c=*) [[]backlog[]]",
        "depth=1 calls=*sample7args.py:*  call         => two(a=*, b=*, c=*) [[]backlog[]]",
        "depth=2 calls=*sample7args.py:*  call            => three(a=*, b=*, c=*) [[]backlog[]]",
        "depth=3 calls=*sample7args.py:*  call               => four(a=*, b=*, c=*) [[]backlog[]]",
        "depth=4 calls=*sample7args.py:*  call                  => five(a=*, b=*, c=*)*",
        "depth=5 calls=*sample7args.py:*  line                     six()*",
        "depth=5 calls=*sample7args.py:*  line                     a = b = c[[]'side'[]] = in_five = 'effect'*",
        "depth=5 calls=*sample7args.py:*  line                     for i in range(1):  # five*",
        "depth=5 calls=*sample7args.py:*  line                     return i  # five",
        "depth=4 calls=*sample7args.py:*  return                <= five: 0",
        "depth=0 calls=*sample7args.py:*  call      => one(a=*, b=*, c=*) [[]backlog[]]",
        "depth=1 calls=*sample7args.py:*  call         => two(a=*, b=*, c=*) [[]backlog[]]",
        "depth=2 calls=*sample7args.py:*  call            => three(a=*, b=*, c=*) [[]backlog[]]",
        "depth=3 calls=*sample7args.py:*  call               => four(a=*, b=*, c=*) [[]backlog[]]",
        "depth=4 calls=*sample7args.py:*  call                  => five(a=*, b=*, c=*)*",
        "depth=5 calls=*sample7args.py:*  line                     six()*",
        "depth=5 calls=*sample7args.py:*  line                     a = b = c[[]'side'[]] = in_five = 'effect'*",
        "depth=5 calls=*sample7args.py:*  line                     for i in range(1):  # five*",
        "depth=5 calls=*sample7args.py:*  line                     return i  # five",
        "depth=4 calls=*sample7args.py:*  return                <= five: 0",
    ])


@pytest.mark.skipif("PY3")
def test_packed_arguments(LineMatcher):
    lines = StringIO()

    with trace(module='sample9py2', action=CallPrinter(stream=lines)):
        from sample9py2 import foo
        foo(1, (2, ), (3, 4), (5, (6, 7), 8))

    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "* call      => foo(a=1, (b,)=(2,), (c, d)=(3, 4), (e, (f, g), h)=(5, (6, 7), 8))",
        "* line         def foo(a, (b,), (c, d), (e, (f, g), h)):",
        "* return    <= foo: None",
    ])

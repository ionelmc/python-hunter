from __future__ import print_function

import inspect
import os
import platform
import subprocess
import sys
import threading
from pprint import pprint

import pytest

import hunter
from hunter import And
from hunter import CallPrinter
from hunter import CodePrinter
from hunter import Debugger
from hunter import Not
from hunter import Or
from hunter import Q
from hunter import Query
from hunter import VarsPrinter
from hunter import When

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
try:
    from itertools import izip_longest
except ImportError:
    from itertools import zip_longest as izip_longest

pytest_plugins = 'pytester',


class FakeCallable(object):
    def __init__(self, value):
        self.value = value

    def __call__(self):
        raise NotImplementedError("Nope")

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)


C = FakeCallable


class EvilTracer(object):
    def __init__(self, *args, **kwargs):
        self._calls = []
        threading_support = kwargs.pop('threading_support', False)
        clear_env_var = kwargs.pop('clear_env_var', False)
        self.handler = hunter._prepare_predicate(*args, **kwargs)
        self._tracer = hunter.trace(self._append, threading_support=threading_support, clear_env_var=clear_env_var)

    def _append(self, event):
        # Make sure the lineno is cached. Frames are reused
        # and later on the events would be very broken ..
        event.lineno
        self._calls.append(event)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._tracer.stop()
        predicate = self.handler
        for call in self._calls:
            predicate(call)


trace = EvilTracer


def _get_func_spec(func):
    spec = inspect.getargspec(func)
    return inspect.formatargspec(spec.args, spec.varargs)


def test_pth_activation():
    module_name = os.path.__name__
    expected_module = "{0}.py".format(module_name)
    hunter_env = "action=CodePrinter,module={!r},function=\"join\"".format(module_name)
    func_spec = _get_func_spec(os.path.join)
    expected_call = "call      def join{0}:".format(func_spec)

    output = subprocess.check_output(
        [sys.executable, os.path.join(os.path.dirname(__file__), 'sample.py')],
        env=dict(os.environ, PYTHONHUNTER=hunter_env),
        stderr=subprocess.STDOUT,
    )
    assert expected_module.encode() in output
    assert expected_call.encode() in output


def test_pth_sample4():
    env = dict(os.environ, PYTHONHUNTER="CodePrinter")
    env.pop('COVERAGE_PROCESS_START', None)
    env.pop('COV_CORE_SOURCE', None)
    output = subprocess.check_output(
        [sys.executable, os.path.join(os.path.dirname(__file__), 'sample4.py')],
        env=env,
        stderr=subprocess.STDOUT,
    )
    assert output


def test_pth_sample2(LineMatcher):
    env = dict(os.environ, PYTHONHUNTER="module='__main__',action=CodePrinter")
    env.pop('COVERAGE_PROCESS_START', None)
    env.pop('COV_CORE_SOURCE', None)
    output = subprocess.check_output(
        [sys.executable, os.path.join(os.path.dirname(__file__), 'sample2.py')],
        env=env,
        stderr=subprocess.STDOUT,
    )
    lm = LineMatcher(output.decode('utf-8').splitlines())
    lm.fnmatch_lines([
        '*tests*sample2.py:* call      if __name__ == "__main__":  #*',
        '*tests*sample2.py:* line      if __name__ == "__main__":  #*',
        '*tests*sample2.py:* line          import functools',
        '*tests*sample2.py:* line          def deco(opt):',
        '*tests*sample2.py:* line          @deco(1)',
        '*tests*sample2.py:* call          def deco(opt):',
        '*tests*sample2.py:* line              def decorator(func):',
        '*tests*sample2.py:* line              return decorator',
        '*tests*sample2.py:* return            return decorator',
        '*                 * ...       return value: <function deco*',
        '*tests*sample2.py:* line          @deco(2)',
        '*tests*sample2.py:* call          def deco(opt):',
        '*tests*sample2.py:* line              def decorator(func):',
        '*tests*sample2.py:* line              return decorator',
        '*tests*sample2.py:* return            return decorator',
        '*                 * ...       return value: <function deco*',
        '*tests*sample2.py:* line          @deco(3)',
        '*tests*sample2.py:* call          def deco(opt):',
        '*tests*sample2.py:* line              def decorator(func):',
        '*tests*sample2.py:* line              return decorator',
        '*tests*sample2.py:* return            return decorator',
        '*                 * ...       return value: <function deco*',
        '*tests*sample2.py:* call              def decorator(func):',
        '*tests*sample2.py:* line                  @functools.wraps(func)',
        '*tests*sample2.py:* line                  return wrapper',
        '*tests*sample2.py:* return                return wrapper',
        '*                 * ...       return value: <function foo *',
        '*tests*sample2.py:* call              def decorator(func):',
        '*tests*sample2.py:* line                  @functools.wraps(func)',
        '*tests*sample2.py:* line                  return wrapper',
        '*tests*sample2.py:* return                return wrapper',
        '*                 * ...       return value: <function foo *',
        '*tests*sample2.py:* call              def decorator(func):',
        '*tests*sample2.py:* line                  @functools.wraps(func)',
        '*tests*sample2.py:* line                  return wrapper',
        '*tests*sample2.py:* return                return wrapper',
        '*                 * ...       return value: <function foo *',
        '*tests*sample2.py:* line          foo(',
        "*tests*sample2.py:* line              'a*',",
        "*tests*sample2.py:* line              'b'",
        '*tests*sample2.py:* call                  @functools.wraps(func)',
        '*                 *    |                  def wrapper(*args):',
        '*tests*sample2.py:* line                      return func(*args)',
        '*tests*sample2.py:* call                  @functools.wraps(func)',
        '*                 *    |                  def wrapper(*args):',
        '*tests*sample2.py:* line                      return func(*args)',
        '*tests*sample2.py:* call                  @functools.wraps(func)',
        '*                 *    |                  def wrapper(*args):',
        '*tests*sample2.py:* line                      return func(*args)',
        '*tests*sample2.py:* call          @deco(1)',
        '*                 *    |          @deco(2)',
        '*                 *    |          @deco(3)',
        '*                 *    |          def foo(*args):',
        '*tests*sample2.py:* line              return args',
        '*tests*sample2.py:* return            return args',
        "*                 * ...       return value: ('a*', 'b')",
        "*tests*sample2.py:* return                    return func(*args)",
        "*                 * ...       return value: ('a*', 'b')",
        "*tests*sample2.py:* return                    return func(*args)",
        "*                 * ...       return value: ('a*', 'b')",
        "*tests*sample2.py:* return                    return func(*args)",
        "*                 * ...       return value: ('a*', 'b')",
        "*tests*sample2.py:* line          try:",
        "*tests*sample2.py:* line              None(",
        "*tests*sample2.py:* line                  'a',",
        "*tests*sample2.py:* line                  'b'",
        "*tests*sample2.py:* exception             'b'",
        "*                 * ...       exception value: *",
        "*tests*sample2.py:* line          except:",
        "*tests*sample2.py:* line              pass",
        "*tests*sample2.py:* return            pass",
        "*                   ...       return value: None",
    ])


def test_predicate_str_repr():
    assert repr(Q(module='a', function='b')).endswith("predicates.Query: query_eq=(('function', 'b'), ('module', 'a'))>")
    assert str(Q(module='a', function='b')) == "Query(function='b', module='a')"

    assert repr(Q(module='a')).endswith("predicates.Query: query_eq=(('module', 'a'),)>")
    assert str(Q(module='a')) == "Query(module='a')"

    assert "predicates.When: condition=<hunter." in repr(Q(module='a', action=C('foo')))
    assert "predicates.Query: query_eq=(('module', 'a'),)>, actions=('foo',)>" in repr(Q(module='a', action=C('foo')))
    assert str(Q(module='a', action=C('foo'))) == "When(Query(module='a'), 'foo')"

    assert "predicates.Not: predicate=<hunter." in repr(~Q(module='a'))
    assert "predicates.Query: query_eq=(('module', 'a'),)>>" in repr(~Q(module='a'))
    assert str(~Q(module='a')) == "Not(Query(module='a'))"

    assert "predicates.Or: predicates=(<hunter." in repr(Q(module='a') | Q(module='b'))
    assert "predicates.Query: query_eq=(('module', 'a'),)>, " in repr(Q(module='a') | Q(module='b'))
    assert repr(Q(module='a') | Q(module='b')).endswith("predicates.Query: query_eq=(('module', 'b'),)>)>")
    assert str(Q(module='a') | Q(module='b')) == "Or(Query(module='a'), Query(module='b'))"

    assert "predicates.And: predicates=(<hunter." in repr(Q(module='a') & Q(module='b'))
    assert "predicates.Query: query_eq=(('module', 'a'),)>," in repr(Q(module='a') & Q(module='b'))
    assert repr(Q(module='a') & Q(module='b')).endswith("predicates.Query: query_eq=(('module', 'b'),)>)>")
    assert str(Q(module='a') & Q(module='b')) == "And(Query(module='a'), Query(module='b'))"


def test_predicate_q_deduplicate_callprinter():
    out = repr(Q(CallPrinter(), action=CallPrinter()))
    assert out.startswith('CallPrinter(')


def test_predicate_q_deduplicate_codeprinter():
    out = repr(Q(CodePrinter(), action=CodePrinter()))
    assert out.startswith('CodePrinter(')


def test_predicate_q_deduplicate_callprinter_cls():
    out = repr(Q(CallPrinter(), action=CallPrinter))
    assert out.startswith('CallPrinter(')


def test_predicate_q_deduplicate_codeprinter_cls():
    out = repr(Q(CodePrinter(), action=CodePrinter))
    assert out.startswith('CodePrinter(')


def test_predicate_q_deduplicate_callprinter_inverted():
    out = repr(Q(CallPrinter(), action=CodePrinter()))
    assert out.startswith('CallPrinter(')


def test_predicate_q_deduplicate_codeprinter_inverted():
    out = repr(Q(CodePrinter(), action=CallPrinter()))
    assert out.startswith('CodePrinter(')


def test_predicate_q_deduplicate_callprinter_cls_inverted():
    out = repr(Q(CallPrinter(), action=CodePrinter))
    assert out.startswith('CallPrinter(')


def test_predicate_q_deduplicate_codeprinter_cls_inverted():
    out = repr(Q(CodePrinter(), action=CallPrinter))
    assert out.startswith('CodePrinter(')


def test_predicate_q_action_callprinter():
    out = repr(Q(action=CallPrinter()))
    assert 'condition=<hunter.' in out
    assert 'actions=(CallPrinter' in out


def test_predicate_q_action_codeprinter():
    out = repr(Q(action=CodePrinter()))
    assert 'condition=<hunter.' in out
    assert 'actions=(CodePrinter' in out


def test_predicate_q_nest_1():
    assert repr(Q(Q(module='a'))).endswith("predicates.Query: query_eq=(('module', 'a'),)>")


def test_predicate_q_not_callable():
    exc = pytest.raises(TypeError, Q, 'foobar')
    assert exc.value.args == ("Predicate 'foobar' is not callable.",)


def test_predicate_q_expansion():
    assert Q(C(1), C(2), module=3) == And(C(1), C(2), Q(module=3))
    assert Q(C(1), C(2), module=3, action=C(4)) == When(And(C(1), C(2), Q(module=3)), C(4))
    assert Q(C(1), C(2), module=3, actions=[C(4), C(5)]) == When(And(C(1), C(2), Q(module=3)), C(4), C(5))


def test_predicate_and():
    assert And(C(1), C(2)) == And(C(1), C(2))
    assert Q(module=1) & Q(module=2) == And(Q(module=1), Q(module=2))
    assert Q(module=1) & Q(module=2) & Q(module=3) == And(Q(module=1), Q(module=2), Q(module=3))

    assert (Q(module=1) & Q(module=2))({'module': 3}) == False
    assert (Q(module=1) & Q(function=2))({'module': 1, 'function': 2}) == True

    assert And(1, 2) | 3 == Or(And(1, 2), 3)


def test_predicate_or():
    assert Q(module=1) | Q(module=2) == Or(Q(module=1), Q(module=2))
    assert Q(module=1) | Q(module=2) | Q(module=3) == Or(Q(module=1), Q(module=2), Q(module=3))

    assert (Q(module=1) | Q(module=2))({'module': 3}) == False
    assert (Q(module=1) | Q(module=2))({'module': 2}) == True

    assert Or(1, 2) & 3 == And(Or(1, 2), 3)


def test_tracing_bare(LineMatcher):
    lines = StringIO()
    with hunter.trace(CodePrinter(stream=lines)):
        def a():
            return 1

        b = a()
        b = 2
        try:
            raise Exception("BOOM!")
        except Exception:
            pass
    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*test_hunter.py* call              def a():",
        "*test_hunter.py* line                  return 1",
        "*test_hunter.py* return                return 1",
        "* ...       return value: 1",
    ])


def test_tracing_reinstall(LineMatcher):
    lines = StringIO()
    with hunter.trace(CodePrinter(stream=lines)):
        def foo():
            a = 2
            sys.settrace(sys.gettrace())
            a = 3

        def bar():
            a = 1
            foo()
            a = 4

        bar()
    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*test_hunter.py:*   call              def bar():",
        "*test_hunter.py:*   line                  a = 1",
        "*test_hunter.py:*   line                  foo()",
        "*test_hunter.py:*   call              def foo():",
        "*test_hunter.py:*   line                  a = 2",
        "*test_hunter.py:*   line                  sys.settrace(sys.gettrace())",
        "*test_hunter.py:*   line                  a = 3",
        "*test_hunter.py:*   return                a = 3",
        "*                   ...       return value: None",
        "*test_hunter.py:*   line                  a = 4",
        "*test_hunter.py:*   return                a = 4",
        "*                   ...       return value: None",

    ])


def test_mix_predicates_with_callables():
    hunter._prepare_predicate(Q(module=1) | Q(lambda: 2))
    hunter._prepare_predicate(Q(lambda: 2) | Q(module=1))
    hunter._prepare_predicate(Q(module=1) & Q(lambda: 2))
    hunter._prepare_predicate(Q(lambda: 2) & Q(module=1))

    hunter._prepare_predicate(Q(module=1) | (lambda: 2))
    hunter._prepare_predicate((lambda: 2) | Q(module=1))
    hunter._prepare_predicate(Q(module=1) & (lambda: 2))
    hunter._prepare_predicate((lambda: 2) & Q(module=1))


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
        'Thread-*   *test_hunter.py:*   call              def foo(a=1):',
        'Thread-*   *                   vars      a => 1',
        'Thread-*   *test_hunter.py:*   call         => foo(a=1)',
        'Thread-*   *                   vars      a => 1',
        'MainThread *test_hunter.py:*   call              def foo(a=1):',
        'MainThread *                   vars      a => 1',
        'MainThread *test_hunter.py:*   call         => foo(a=1)',
        'MainThread *                   vars      a => 1',
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
        'Thread-*   *test_hunter.py:*   call              def foo(a=1):',
        'Thread-*   *                   vars      a => 1',
        'Thread-*   *test_hunter.py:*   call         => foo(a=1)',
        'Thread-*   *                   vars      a => 1',
    ])


def test_tracing_printing_failures(LineMatcher):
    lines = StringIO()
    with trace(actions=[CodePrinter(stream=lines), VarsPrinter("x", stream=lines)]):
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
    lm.fnmatch_lines([
        """*tests*test_hunter.py:* call              class Bad(object):""",
        """*tests*test_hunter.py:* line              class Bad(object):""",
        """*tests*test_hunter.py:* line                  def __repr__(self):""",
        """*tests*test_hunter.py:* return                def __repr__(self):""",
        """* ...       return value: *""",
        """*tests*test_hunter.py:* call              def a():""",
        """*tests*test_hunter.py:* line                  x = Bad()""",
        """*tests*test_hunter.py:* line                  return x""",
        """* vars      x => !!! FAILED REPR: RuntimeError("I'm a bad class!"*)""",
        """*tests*test_hunter.py:* return                return x""",
        """* ...       return value: !!! FAILED REPR: RuntimeError("I'm a bad class!"*)""",
        """* vars      x => !!! FAILED REPR: RuntimeError("I'm a bad class!"*)""",
        """*tests*test_hunter.py:* call              def b():""",
        """*tests*test_hunter.py:* line                  x = Bad()""",
        """*tests*test_hunter.py:* line                  raise Exception(x)""",
        """* vars      x => !!! FAILED REPR: RuntimeError("I'm a bad class!"*)""",
        """*tests*test_hunter.py:* exception             raise Exception(x)""",
        """* ...       exception value: !!! FAILED REPR: RuntimeError("I'm a bad class!"*)""",
        """* vars      x => !!! FAILED REPR: RuntimeError("I'm a bad class!"*)""",
        """*tests*test_hunter.py:* return                raise Exception(x)""",
        """* ...       return value: None""",
        """* vars      x => !!! FAILED REPR: RuntimeError("I'm a bad class!"*)""",
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
            raise Exception("BOOM!")
        except Exception:
            pass
    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines([
        "*test_hunter.py* call              def a():",
        "*test_hunter.py* line                  b = 1",
        "* vars      b => 1",
        "*test_hunter.py* line                  b = 2",
        "* vars      b => 2",
        "*test_hunter.py* line                  return 1",
        "* vars      b => 2",
        "*test_hunter.py* return                return 1",
        "* ...       return value: 1",
    ])


def test_tracing_vars_expressions(LineMatcher):
    lines = StringIO()
    with hunter.trace(actions=[VarsPrinter('Foo.bar', 'Foo.__dict__["bar"]', stream=lines)]):
        def main():
            class Foo(object):
                bar = 1

        main()
    print(lines.getvalue())
    lm = LineMatcher(lines.getvalue().splitlines())
    lm.fnmatch_lines_random([
        '*      Foo.bar => 1',
        '*      Foo.__dict__[[]"bar"[]] => 1',
    ])


def test_trace_merge():
    with hunter.trace(function="a"):
        with hunter.trace(function="b"):
            with hunter.trace(function="c"):
                assert sys.gettrace().handler == When(Q(function="c"), CallPrinter)
            assert sys.gettrace().handler == When(Q(function="b"), CallPrinter)
        assert sys.gettrace().handler == When(Q(function="a"), CallPrinter)


def test_trace_api_expansion():
    # simple use
    with trace(function="foobar") as t:
        assert t.handler == When(Q(function="foobar"), CallPrinter)

    # "or" by expression
    with trace(module="foo", function="foobar") as t:
        assert t.handler == When(Q(module="foo", function="foobar"), CallPrinter)

    # pdb.set_trace
    with trace(function="foobar", action=Debugger) as t:
        assert str(t.handler) == str(When(Q(function="foobar"), Debugger))

    # pdb.set_trace on any hits
    with trace(module="foo", function="foobar", action=Debugger) as t:
        assert str(t.handler) == str(When(Q(module="foo", function="foobar"), Debugger))

    # pdb.set_trace when function is foobar, otherwise just print when module is foo
    with trace(Q(function="foobar", action=Debugger), module="foo") as t:
        assert str(t.handler) == str(When(And(
            When(Q(function="foobar"), Debugger),
            Q(module="foo")
        ), CallPrinter))

    # dumping variables from stack
    with trace(Q(function="foobar", action=VarsPrinter("foobar")), module="foo") as t:
        assert str(t.handler) == str(When(And(
            When(Q(function="foobar"), VarsPrinter("foobar")),
            Q(module="foo"),
        ), CallPrinter))

    with trace(Q(function="foobar", action=VarsPrinter("foobar", "mumbojumbo")), module="foo") as t:
        assert str(t.handler) == str(When(And(
            When(Q(function="foobar"), VarsPrinter("foobar", "mumbojumbo")),
            Q(module="foo"),
        ), CallPrinter))

    # multiple actions
    with trace(Q(function="foobar", actions=[VarsPrinter("foobar"), Debugger]), module="foo") as t:
        assert str(t.handler) == str(When(And(
            When(Q(function="foobar"), VarsPrinter("foobar"), Debugger),
            Q(module="foo"),
        ), CallPrinter))


def test_locals():
    out = StringIO()
    with hunter.trace(
        lambda event: event.locals.get("node") == "Foobar",
        module="test_hunter",
        function="foo",
        action=CodePrinter(stream=out)
    ):
        def foo():
            a = 1
            node = "Foobar"
            node += "x"
            a += 2
            return a

        foo()
    assert out.getvalue().endswith('node += "x"\n')


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
        '*    |              def foo():',
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


@pytest.mark.skipif('os.environ.get("SETUPPY_CFLAGS") == "-DCYTHON_TRACE=1"')
def test_wraps(LineMatcher):
    calls = []

    @hunter.wrap(action=lambda event: calls.append("%06s calls=%s depth=%s %s" % (event.kind, event.calls, event.depth, event.fullsource)))
    def foo():
        return 1

    foo()
    lm = LineMatcher(calls)
    lm.fnmatch_lines([
        '  call calls=0 depth=0     @hunter.wrap*',
        '  line calls=1 depth=1         return 1\n',
        'return calls=1 depth=1         return 1\n',
    ])


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
    assert ('call', 'test_hunter', 'bar', 1) in calls
    assert ('return', 'test_hunter', 'foo', 1) in calls


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


def test_debugger(LineMatcher):
    out = StringIO()
    calls = []

    class FakePDB:
        def __init__(self, foobar=1):
            calls.append(foobar)

        def set_trace(self, frame):
            calls.append(frame.f_code.co_name)

    with hunter.trace(
        lambda event: event.locals.get("node") == "Foobar",
        module="test_hunter",
        function="foo",
        actions=[CodePrinter,
                 VarsPrinter("a", "node", "foo", "test_debugger", globals=True, stream=out),
                 Debugger(klass=FakePDB, foobar=2)]
    ):
        def foo():
            a = 1
            node = "Foobar"
            node += "x"
            a += 2
            return a

        foo()
    print(out.getvalue())
    assert calls == [2, 'foo']
    lm = LineMatcher(out.getvalue().splitlines())
    pprint(lm.lines)
    lm.fnmatch_lines_random([
        "*      test_debugger => <function test_debugger at *",
        "*      node => 'Foobar'",
        "*      a => 1",
    ])


def test_custom_action():
    calls = []

    with trace(action=lambda event: calls.append(event.function), kind="return"):
        def foo():
            return 1

        foo()
    assert 'foo' in calls


def test_trace_with_class_actions():
    with trace(CodePrinter):
        def a():
            pass

        a()


def test_predicate_no_inf_recursion():
    assert Or(And(1)) == 1
    assert Or(Or(1)) == 1
    assert And(Or(1)) == 1
    assert And(And(1)) == 1
    predicate = Q(Q(lambda ev: 1, module='wat'))
    print('predicate:', predicate)
    predicate({'module': 'foo'})


def test_predicate_compression():
    assert Or(Or(1, 2), And(3)) == Or(1, 2, 3)
    assert Or(Or(1, 2), 3) == Or(1, 2, 3)
    assert Or(1, Or(2, 3), 4) == Or(1, 2, 3, 4)
    assert And(1, 2, Or(3, 4)).predicates == (1, 2, Or(3, 4))

    assert repr(Or(Or(1, 2), And(3))) == repr(Or(1, 2, 3))
    assert repr(Or(Or(1, 2), 3)) == repr(Or(1, 2, 3))
    assert repr(Or(1, Or(2, 3), 4)) == repr(Or(1, 2, 3, 4))


def test_predicate_not():
    assert Not(1).predicate == 1
    assert ~Or(1, 2) == Not(Or(1, 2))
    assert ~And(1, 2) == Not(And(1, 2))

    assert ~Not(1) == 1

    assert ~Query(module=1) | ~Query(module=2) == Not(And(Query(module=1), Query(module=2)))
    assert ~Query(module=1) & ~Query(module=2) == Not(Or(Query(module=1), Query(module=2)))

    assert ~Query(module=1) | Query(module=2) == Or(Not(Query(module=1)), Query(module=2))
    assert ~Query(module=1) & Query(module=2) == And(Not(Query(module=1)), Query(module=2))

    assert ~(Query(module=1) & Query(module=2)) == Not(And(Query(module=1), Query(module=2)))
    assert ~(Query(module=1) | Query(module=2)) == Not(Or(Query(module=1), Query(module=2)))

    assert repr(~Or(1, 2)) == repr(Not(Or(1, 2)))
    assert repr(~And(1, 2)) == repr(Not(And(1, 2)))

    assert repr(~Query(module=1) | ~Query(module=2)) == repr(Not(And(Query(module=1), Query(module=2))))
    assert repr(~Query(module=1) & ~Query(module=2)) == repr(Not(Or(Query(module=1), Query(module=2))))

    assert repr(~(Query(module=1) & Query(module=2))) == repr(Not(And(Query(module=1), Query(module=2))))
    assert repr(~(Query(module=1) | Query(module=2))) == repr(Not(Or(Query(module=1), Query(module=2))))

    assert Not(Q(module=1))({'module': 1}) == False


def test_predicate_query_allowed():
    pytest.raises(TypeError, Query, 1)
    pytest.raises(TypeError, Query, a=1)


def test_predicate_when_allowed():
    pytest.raises(TypeError, When, 1)


@pytest.mark.parametrize('expr,inp,expected', [
    ({'module': "abc"}, {'module': "abc"}, True),
    ({'module': "abcd"}, {'module': "abc"}, False),
    ({'module': "abcd"}, {'module': "abce"}, False),
    ({'module_startswith': "abc"}, {'module': "abcd"}, True),
    ({'module__startswith': "abc"}, {'module': "abcd"}, True),
    ({'module_contains': "bc"}, {'module': "abcd"}, True),
    ({'module_contains': "bcde"}, {'module': "abcd"}, False),

    ({'module_endswith': "abc"}, {'module': "abcd"}, False),
    ({'module__endswith': "bcd"}, {'module': "abcd"}, True),

    ({'module_in': "abcd"}, {'module': "bc"}, True),
    ({'module': "abcd"}, {'module': "bc"}, False),
    ({'module': ["abcd"]}, {'module': "bc"}, False),
    ({'module_in': ["abcd"]}, {'module': "bc"}, False),
    ({'module_in': ["a", "bc", "d"]}, {'module': "bc"}, True),

    ({'module': "abcd"}, {'module': "abc"}, False),

    ({'module_startswith': ("abc", "xyz")}, {'module': "abc"}, True),
    ({'module_startswith': {"abc", "xyz"}}, {'module': "abc"}, True),
    ({'module_startswith': ["abc", "xyz"]}, {'module': "abc"}, True),
    ({'module_startswith': ("abc", "xyz")}, {'module': "abcd"}, True),
    ({'module_startswith': ("abc", "xyz")}, {'module': "xyzw"}, True),
    ({'module_startswith': ("abc", "xyz")}, {'module': "fooabc"}, False),

    ({'module_endswith': ("abc", "xyz")}, {'module': "abc"}, True),
    ({'module_endswith': {"abc", "xyz"}}, {'module': "abc"}, True),
    ({'module_endswith': ["abc", "xyz"]}, {'module': "abc"}, True),
    ({'module_endswith': ("abc", "xyz")}, {'module': "1abc"}, True),
    ({'module_endswith': ("abc", "xyz")}, {'module': "1xyz"}, True),
    ({'module_endswith': ("abc", "xyz")}, {'module': "abcfoo"}, False),

    ({'module': "abc"}, {'module': 1}, False),

    ({'module_regex': r"(re|sre.*)\b"}, {'module': "regex"}, False),
    ({'module_regex': r"(re|sre.*)\b"}, {'module': "re.gex"}, True),
    ({'module_regex': r"(re|sre.*)\b"}, {'module': "sregex"}, True),
    ({'module_regex': r"(re|sre.*)\b"}, {'module': "re"}, True),
])
def test_predicate_matching(expr, inp, expected):
    assert Query(**expr)(inp) == expected


@pytest.mark.parametrize('exc_type,expr', [
    (TypeError, {'module_1': 1}),
    (TypeError, {'module1': 1}),
    (ValueError, {'module_startswith': 1}),
    (ValueError, {'module_startswith': {1: 2}}),
    (ValueError, {'module_endswith': 1}),
    (ValueError, {'module_endswith': {1: 2}}),
    (TypeError, {'module_foo': 1}),
    (TypeError, {'module_a_b': 1}),
])
def test_predicate_bad_query(expr, exc_type):
    pytest.raises(exc_type, Query, **expr)


def test_predicate_when():
    called = []
    assert When(Q(module=1), lambda ev: called.append(ev))({'module': 2}) == False
    assert called == []

    assert When(Q(module=1), lambda ev: called.append(ev))({'module': 1}) == True
    assert called == [{'module': 1}]

    called = []
    assert Q(module=1, action=lambda ev: called.append(ev))({'module': 1}) == True
    assert called == [{'module': 1}]

    called = [[], []]
    predicate = (
        Q(module=1, action=lambda ev: called[0].append(ev)) |
        Q(module=2, action=lambda ev: called[1].append(ev))
    )
    assert predicate({'module': 1}) == True
    assert called == [[{'module': 1}], []]

    assert predicate({'module': 2}) == True
    assert called == [[{'module': 1}], [{'module': 2}]]

    called = [[], []]
    predicate = (
        Q(module=1, action=lambda ev: called[0].append(ev)) &
        Q(function=2, action=lambda ev: called[1].append(ev))
    )
    assert predicate({'module': 2}) == False
    assert called == [[], []]

    assert predicate({'module': 1, 'function': 2}) == True
    assert called == [[{'module': 1, 'function': 2}], [{'module': 1, 'function': 2}]]


def test_and_or_kwargs():
    assert And(1, function=2) == And(1, Query(function=2))
    assert Or(1, function=2) == Or(1, Query(function=2))


def test_proper_backend():
    if os.environ.get('PUREPYTHONHUNTER') or platform.python_implementation() == 'PyPy':
        assert 'hunter.tracer.Tracer' in repr(hunter.Tracer)
    else:
        assert 'hunter._tracer.Tracer' in repr(hunter.Tracer)


@pytest.fixture(scope="session", params=['pure', 'cython'])
def tracer_impl(request):
    if request.param == 'pure':
        return pytest.importorskip('hunter.tracer').Tracer
    elif request.param == 'cython':
        return pytest.importorskip('hunter._tracer').Tracer


def _bulky_func_that_use_stdlib():
    import difflib
    a = list(map(str, range(500)))
    b = list(map(str, range(0, 500, 2)))
    list(difflib.unified_diff(a, b, 'a', 'b'))


def test_perf_filter(tracer_impl, benchmark):
    t = tracer_impl()

    @benchmark
    def run():
        output = StringIO()
        with t.trace(Q(
            Q(module="does-not-exist") | Q(module="does not exist".split()),
            action=CodePrinter(stream=output)
        )):
            _bulky_func_that_use_stdlib()
        return output

    assert run.getvalue() == ''


def test_perf_stdlib(tracer_impl, benchmark):
    t = tracer_impl()

    @benchmark
    def run():
        output = StringIO()
        with t.trace(Q(
            ~Q(module_contains='pytest'),
            ~Q(module_contains='hunter'),
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
            ~Q(module_in=['re', 'sre', 'sre_parse']) & ~Q(module_startswith='namedtuple') & Q(kind="call"),
            actions=[
                CodePrinter(
                    stream=output
                ),
                VarsPrinter(
                    'line',
                    globals=True,
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

    assert os.environ.get('PYTHONHUNTER') == None


@pytest.mark.skipif(sys.platform == 'win32', reason="no fork on windows")
@pytest.mark.parametrize('Action', [CodePrinter, CallPrinter])
@pytest.mark.parametrize('force_pid', [True, False])
def test_pid_prefix(LineMatcher, Action, force_pid, capfd):
    def main():
        a = 1
        pid = os.fork()
        if pid:
            os.waitpid(pid, 0)
        else:
            os._exit(0)  # child

    with hunter.trace(actions=[Action(force_pid=force_pid, stream=sys.stdout),
                               VarsPrinter('a', force_pid=force_pid, stream=sys.stdout)],
                      stdlib=False,
                      threading_support=True):
        main()
    out, err = capfd.readouterr()
    print('OUT', out)
    print('ERR', err)
    lm = LineMatcher(out.splitlines())
    prefix = '[[]*[]] * ' if force_pid else ''
    lm.fnmatch_lines([
        prefix + "MainThread  *test_hunter.py:*  line * a = 1",
        prefix + "MainThread  *test_hunter.py:*  line * if pid:",
        prefix + "MainThread  *               *  vars * a => 1",
        prefix + "MainThread  *test_hunter.py:*  line * os.waitpid(pid, 0)",
        "[[]*[]] * MainThread  *test_hunter.py:*  line * os._exit(0)  # child",
        "[[]*[]] * MainThread  *               *  vars * a => 1",
    ])

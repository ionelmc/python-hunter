from __future__ import print_function

import os
import subprocess
from fnmatch import fnmatchcase
from io import StringIO
try:
    from itertools import izip_longest
except ImportError:
    from itertools import zip_longest as izip_longest

import pytest

from hunter import And
from hunter import Q
from hunter import Or
from hunter import stop
from hunter import trace
from hunter import When

from hunter import CodePrinter
from hunter import Debugger
from hunter import VarsPrinter


@pytest.yield_fixture(autouse=True, scope="function")
def auto_stop():
    try:
        yield
    finally:
        stop()


def test_pth_activation():
    output = subprocess.check_output(
        ['python', os.path.join(os.path.dirname(__file__), 'sample.py')],
        env=dict(os.environ, PYTHONHUNTER="module='posixpath',function=\"join\""),
        stderr=subprocess.STDOUT,
    )
    assert b"posixpath.py" in output
    assert b"call      def join(a, *p):" in output

def test_repr():
    assert repr(Q(module='a')) == "Query(module='a')"
    assert str(Q(module='a')) == "Query(module='a')"
    assert repr(Q(module='a', action='foo')) == "When(condition=Query(module='a'), actions=['foo'])"


def test_nest_1():
    assert repr(Q(Q(module='a'))) == "Query(module='a')"


def test_expansion():
    assert Q(1, 2, module=3) == Or(1, 2, Q(module=3))
    assert Q(1, 2, module=3, action=4) == When(Or(1, 2, Q(module=3)), 4)
    assert Q(1, 2, module=3, actions=[4, 5]) == When(Or(1, 2, Q(module=3)), 4, 5)


def test_and():
    assert Q(module=1) & Q(module=2) == And(Q(module=1), Q(module=2))
    assert Q(module=1) & Q(module=2) & Q(module=3) == And(Q(module=1), Q(module=2), Q(module=3))


def test_or():
    assert Q(module=1) | Q(module=2) == Or(Q(module=1), Q(module=2))
    assert Q(module=1) | Q(module=2) | Q(module=3) == Or(Q(module=1), Q(module=2), Q(module=3))


def test_tracing_bare():
    lines = StringIO()
    with trace(CodePrinter(stream=lines)):
        def a():
            return 1
        b = a()
        b = 2
        try:
            raise Exception("BOOM!")
        except Exception:
            pass
    print(lines.getvalue())

    for line, expected in izip_longest(lines.getvalue().splitlines(), [
        "*      */hunter.py* call          def __enter__(self):",
        "*      */hunter.py* line              return self",
        "*      */hunter.py* return            return self",
        "*                 * ...       return value: <hunter.Tracer *",
        "* */test_hunter.py* call              def a():",
        "* */test_hunter.py* line                  return 1",
        "* */test_hunter.py* return                return 1",
        "*                 * ...       return value: 1",
        "*      */hunter.py* call          def __exit__(self, exc_type, exc_val, exc_tb):",
        "*      */hunter.py* line              self.stop()",
        "*      */hunter.py* call          def stop(self):",
        "*      */hunter.py* line              sys.settrace(self._previous_tracer)",
    ], fillvalue="MISSING"):
        assert fnmatchcase(line, expected), "%r didn't match %r" % (line, expected)


def test_tracing_vars():
    lines = StringIO()
    with trace(actions=[VarsPrinter('b', stream=lines), CodePrinter(stream=lines)]):
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

    for line, expected in izip_longest(lines.getvalue().splitlines(), [
        "*      */hunter.py* call          def __enter__(self):",
        "*      */hunter.py* line              return self",
        "*      */hunter.py* return            return self",
        "*                 * ...       return value: <hunter.Tracer *",
        "* */test_hunter.py* call              def a():",
        "* */test_hunter.py* line                  b = 1",
        "*                 * vars      b => 1",
        "* */test_hunter.py* line                  b = 2",
        "*                 * vars      b => 2",
        "* */test_hunter.py* line                  return 1",
        "*                 * vars      b => 2",
        "* */test_hunter.py* return                return 1",
        "*                 * ...       return value: 1",
        "*      */hunter.py* call          def __exit__(self, exc_type, exc_val, exc_tb):",
        "*      */hunter.py* line              self.stop()",
        "*      */hunter.py* call          def stop(self):",
        "*      */hunter.py* line              sys.settrace(self._previous_tracer)",
    ], fillvalue="MISSING"):
        assert fnmatchcase(line, expected), "%r didn't match %r" % (line, expected)


def test_trace_merge():
    trace(function="a")
    trace(function="b")
    assert trace(function="c")._handler == Or(
        When(Q(function="a"), CodePrinter),
        When(Q(function="b"), CodePrinter),
        When(Q(function="c"), CodePrinter),
    )


def test_trace_api_expansion():
    # simple use
    with trace(function="foobar") as t:
        assert t._handler == When(Q(function="foobar"), CodePrinter)

    # "or" by expression
    with trace(module="foo", function="foobar") as t:
        assert t._handler == When(Q(module="foo", function="foobar"), CodePrinter)

    # pdb.set_trace
    with trace(function="foobar", action=Debugger) as t:
        assert t._handler == When(Q(function="foobar"), Debugger)

    # pdb.set_trace on any hits
    with trace(module="foo", function="foobar", action=Debugger) as t:
        assert t._handler == When(Q(module="foo", function="foobar"), Debugger)

    # pdb.set_trace when function is foobar, otherwise just print when module is foo
    with trace(Q(function="foobar", action=Debugger), module="foo") as t:
        assert t._handler == When(Or(
            When(Q(function="foobar"), Debugger),
            Q(module="foo")
        ), CodePrinter)

    # dumping variables from stack
    with trace(Q(function="foobar", action=VarsPrinter("foobar")), module="foo") as t:
        assert t._handler == When(Or(
            When(Q(function="foobar"), VarsPrinter("foobar")),
            Q(module="foo"),
        ), CodePrinter)

    with trace(Q(function="foobar", action=VarsPrinter("foobar", "mumbojumbo")), module="foo") as t:
        assert t._handler == When(Or(
            When(Q(function="foobar"), VarsPrinter("foobar", "mumbojumbo")),
            Q(module="foo"),
        ), CodePrinter)

    # multiple actions
    with trace(Q(function="foobar", actions=[VarsPrinter("foobar"), Debugger]), module="foo") as t:
        assert t._handler == When(Or(
            When(Q(function="foobar"), VarsPrinter("foobar"), Debugger),
            Q(module="foo"),
        ), CodePrinter)

    # customization
    assert trace(lambda event: event.locals.get("node") == "Foobar",
                 module="foo", function="foobar")
    assert trace(Q(lambda event: event.locals.get("node") == "Foobar",
                   function="foobar", actions=[VarsPrinter("foobar"), Debugger]), module="foo",)
    assert trace(Q(function="foobar", actions=[VarsPrinter("foobar"),
                                               lambda event: print("some custom output")]), module="foo",)

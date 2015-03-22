from __future__ import print_function

import os
import subprocess
from io import StringIO
from fnmatch import fnmatchcase

import pytest

from hunter import And
from hunter import F
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


@pytest.mark.skipif('TESTS_EXPECT_PTH' not in os.environ, reason="hunter.pth file is not available in this env.")
def test_pth_activation():
    output = subprocess.check_output(
        ['python', os.path.join(os.path.dirname(__file__), 'sample.py')],
        env=dict(os.environ, PYTHON_HUNTER="module='posixpath',function=\"join\""),
        stderr=subprocess.STDOUT,
    )
    assert b"posixpath.py" in output
    assert b"call      def join(a, *p):" in output


def test_expansion():
    assert F(1, 2, module=3) == Or(1, 2, F(module=3))
    assert F(1, 2, module=3, action=4) == When(Or(1, 2, F(module=3)), actions=[4])


def test_and():
    assert F(module=1) & F(module=2) == And(F(module=1), F(module=2))
    assert F(module=1) & F(module=2) & F(module=3) == And(F(module=1), F(module=2), F(module=3))


def test_or():
    assert F(module=1) | F(module=2) == Or(F(module=1), F(module=2))
    assert F(module=1) | F(module=2) | F(module=3) == Or(F(module=1), F(module=2), F(module=3))


def test_tracing_bare():
    lines = StringIO()
    with trace():
        def a():
            return 1
        b = a()
        b = 2
        try:
            raise Exception("BOOM!")
        except Exception:
            pass
    print(lines.getvalue())

    for line, expected in zip(lines.getvalue().splitlines(), [
        r"      hunter.py*    call          def __enter__(self):",
        r"      hunter.py*    line              return self",
        r"      hunter.py*    return            return self",
        r"               *    ...       return value: Tracer(_handler=When(condition=F(query={}), actions=*",
        r" test_hunter.py*    call              def a():",
        r" test_hunter.py*    line                  return 1",
        r" test_hunter.py*    return                return 1",
        r"               *    ...       return value: 1",
        r"      hunter.py*    call          def __exit__(self, exc_type, exc_val, exc_tb):",
        r"      hunter.py*    line              self.stop()",
        r"      hunter.py*    call          def stop(self):",
        r"      hunter.py*    line              sys.settrace(self._previous_tracer)"
    ]):
        assert fnmatchcase(line, expected), "%r didn't match %r" % (line, expected)


def test_tracing_vars():
    lines = StringIO()
    with trace(actions=[VarsPrinter(name='b', stream=lines), CodePrinter(stream=lines)]):
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

    for line, expected in zip(lines.getvalue().splitlines(), [
        "      hunter.py*    call          def __enter__(self):",
        "      hunter.py*    line              return self",
        "      hunter.py*    return            return self",
        "               *    ...       return value: <hunter.Tracer *",
        " test_hunter.py*    call              def a():",
        " test_hunter.py*    line                  b = 1",
        "               *    vars      b -> 1",
        " test_hunter.py*    line                  b = 2",
        "               *    vars      b -> 2",
        " test_hunter.py*    line                  return 1",
        "               *    vars      b -> 2",
        " test_hunter.py*    return                return 1",
        "               *    ...       return value: 1",
        "      hunter.py*    call          def __exit__(self, exc_type, exc_val, exc_tb):",
        "      hunter.py*    line              self.stop()",
        "      hunter.py*    call          def stop(self):",
        "      hunter.py*    line              sys.settrace(self._previous_tracer)",
    ]):
        assert fnmatchcase(line, expected), "%r didn't match %r" % (line, expected)


def test_trace_merge():
    trace(function="a")
    trace(function="b")
    assert trace(function="c")._handler == Or(
        When(F(function="a"), actions=[CodePrinter]),
        When(F(function="b"), actions=[CodePrinter]),
        When(F(function="c"), actions=[CodePrinter]),
    )


def test_trace_api_expansion():
    # simple use
    with trace(function="foobar") as t:
        assert t._handler == When(F(function="foobar"), actions=[CodePrinter])

    # "or" by expression
    with trace(module="foo", function="foobar") as t:
        assert t._handler == When(F(module="foo", function="foobar"), actions=[CodePrinter])

    # pdb.set_trace
    with trace(function="foobar", action=Debugger) as t:
        assert t._handler == When(F(function="foobar"), actions=[Debugger])

    # pdb.set_trace on any hits
    with trace(module="foo", function="foobar", action=Debugger) as t:
        assert t._handler == When(F(module="foo", function="foobar"), actions=[Debugger])

    # pdb.set_trace when function is foobar, otherwise just print when module is foo
    with trace(F(function="foobar", action=Debugger), module="foo") as t:
        assert t._handler == When(Or(
            When(F(function="foobar"), actions=[Debugger]),
            F(module="foo")
        ), actions=[CodePrinter])

    # dumping variables from stack
    with trace(F(function="foobar", action=VarsPrinter(name="foobar")), module="foo") as t:
        assert t._handler == When(Or(
            When(F(function="foobar"), actions=[VarsPrinter(name="foobar")]),
            F(module="foo"),
        ), actions=[CodePrinter])

    with trace(F(function="foobar", action=VarsPrinter(names=["foobar", "mumbojumbo"])), module="foo") as t:
        assert t._handler == When(Or(
            When(F(function="foobar"), actions=[VarsPrinter(names=["foobar", "mumbojumbo"])]),
            F(module="foo"),
        ), actions=[CodePrinter])

    # multiple actions
    with trace(F(function="foobar", actions=[VarsPrinter(name="foobar"), Debugger]), module="foo") as t:
        assert t._handler == When(Or(
            When(F(function="foobar"), actions=[VarsPrinter(name="foobar"), Debugger]),
            F(module="foo"),
        ), actions=[CodePrinter])

    # customization
    assert trace(lambda event: event.locals.get("node") == "Foobar",
                 module="foo", function="foobar")
    assert trace(F(lambda event: event.locals.get("node") == "Foobar",
                   function="foobar", actions=[VarsPrinter(name="foobar"), Debugger]), module="foo",)
    assert trace(F(function="foobar", actions=[VarsPrinter(name="foobar"),
                                               lambda event: print("some custom output")]), module="foo",)


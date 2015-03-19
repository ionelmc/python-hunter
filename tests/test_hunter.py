from __future__ import print_function

import pytest

from hunter import F, And, Or, CodePrinter, When, trace, stop, VarsDumper, Debugger

@pytest.yield_fixture(autouse=True, scope="function")
def auto_stop():
    try:
        yield
    finally:
        stop()


def test_expand_F():
    assert F(1, 2, module=3) == Or(1, 2, F(module=3))
    assert F(1, 2, module=3, action=4) == When(Or(1, 2, F(module=3)), actions=[4])


def test_trace():
    assert CodePrinter() == CodePrinter()

    # simple use
    assert trace(function="foobar").predicate == When(F(function="foobar"), actions=[CodePrinter()])

    # "or" by expression
    assert trace(module="foo", function="foobar").predicate == When(F(module="foo", function="foobar"), actions=[CodePrinter()])

    # pdb.set_trace
    assert trace(function="foobar", action=Debugger)

    # pdb.set_trace on any hits
    assert trace(module="foo", function="foobar", action=Debugger)

    # pdb.set_trace when function is foobar, otherwise just print when module is foo
    assert trace(F(function="foobar", action=Debugger), module="foo")

    # dumping variables from stack
    assert trace(F(function="foobar", action=VarsDumper(name="foobar")), module="foo")
    assert trace(F(function="foobar", action=VarsDumper(names=["foobar", "mumbojumbo"])), module="foo")

    # multiple actions
    assert trace(F(function="foobar", actions=[VarsDumper(name="foobar"), Debugger]), module="foo",)

    # customization
    assert trace(lambda event: event.locals.get("node") == "Foobar",
                 module="foo", function="foobar")
    assert trace(F(lambda event: event.locals.get("node") == "Foobar",
                   function="foobar", actions=[VarsDumper(name="foobar"), Debugger]), module="foo",)
    assert trace(F(function="foobar", actions=[VarsDumper(name="foobar"),
                                               lambda event: print("some custom output")]), module="foo",)

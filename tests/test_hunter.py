from hunter.__main__ import main


def test_main():
    assert main([]) == 0

# simple use
hunter.trace(Named(function="foobar"))

# "or" by expression
hunter.trace(Named(module="foo") | Named(function="foobar"))

# "or" by verbose
hunter.trace(Or(Named(module="foo"), Named(function="foobar")))

# pdb.set_trace
hunter.trace(Named(function="foobar"), action=Pdb)

# pdb.set_trace on all hits
hunter.trace(Named(module="foo") | Named(function="foobar"), action=Pdb)

# pdb.set_trace when function is foobar
hunter.trace(Named(module="foo") | Action(Named(function="foobar"), Pdb))

# dumping variables from stack
hunter.trace(Named(module="foo") | Action(Named(function="foobar"),
                                          DumpVars(Named("foobar"))))

# multiple actions
hunter.trace(Named(module="foo") | Action(Named(function="foobar"),
                                          DumpVars(Named("foobar")),
                                          Pdb))
from hunter import trace, Or, Named, Action, Pdb, DumpVars

trace(
    Or(
        Named(module="foo"),
        Action(
            Named(function="foobar"),
            DumpVars(Named("foobar")),
            Pdb
        )
    )
)

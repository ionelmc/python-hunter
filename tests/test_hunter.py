"""

These are some API ideas for a "flexible" tracer tool, not for measuring coverage, but for debugging, logging, inspection and other
nefarious purposes.

The idea is that the user gives the tracer a tree-like configuration where he optionally can configure specific actions for parts of the
tree (like dumping variables or a pdb set_trace).

The default action is to just print the code being executed.
"""


######################

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
hunter.trace(Named(module="foo") | Action(Named(function="foobar"), DumpVars(Named("foobar"))))

# multiple actions
hunter.trace(Named(module="foo") | Action(Named(function="foobar"), DumpVars(Named("foobar")), Pdb))

from hunter import trace, Or, Named, Action, Pdb, DumpVars

hunter.trace(Or(Named(module="foo"), Action(Named(function="foobar"), DumpVars(Named("foobar")), Pdb)))

###########
###########
# Using When expression

# pdb.set_trace when function is foobar
hunter.trace(Named(module="foo") | When(Named(function="foobar"), action=Pdb))

# dumping variables from stack
hunter.trace(Named(module="foo") | When(Named(function="foobar"), action=DumpVars(Named("foobar"))))

# multiple actions
hunter.trace(Named(module="foo") | Wehn(Named(function="foobar"), actions=[DumpVars(Named("foobar")), Pdb]))

###########
###########
# Defaulting to or

# pdb.set_trace when function is foobar
hunter.trace(Named(module="foo") | When(Named(function="foobar"), action=Pdb))

# dumping variables from stack
hunter.trace(Named(module="foo") | When(Named(function="foobar"), action=DumpVars(Named("foobar"))))

# multiple actions
hunter.trace(Named(module="foo") | Wehn(Named(function="foobar"), actions=[DumpVars(Named("foobar")), Pdb]))


############################################
############################################
############################################
# The short way, and OR is default

# simple use
hunter.trace(function="foobar")

# "or" by expression
hunter.trace(module="foo", function="foobar")

# "or" by verbose
#hunter.trace(Or(F(module="foo"), F(function="foobar")))

# pdb.set_trace
hunter.trace(function="foobar", action=Pdb)

# pdb.set_trace on any hits
hunter.trace(module="foo", function="foobar", action=Pdb)

# pdb.set_trace when function is foobar, otherwise just print when module is foo
hunter.trace(F(function="foobar", action=Pdb), module="foo")

# dumping variables from stack
hunter.trace(F(function="foobar", action=DumpVars(name="foobar")), module="foo")
hunter.trace(F(function="foobar", action=DumpVars(names=["foobar", "mumbojumbo"])), module="foo")

# multiple actions
hunter.trace(F(function="foobar", actions=[DumpVars(name="foobar"), Pdb]), module="foo",)

############################################
############################################
############################################
# fancy query language

# simple use
hunter.trace(F.function == "foobar")

# "or" by expression
hunter.trace(F.module == "foo", F.function == "foobar")

# "or" by verbose
#hunter.trace(Or(F(module="foo"), F(function="foobar")))

# pdb.set_trace
hunter.trace(F.function == "foobar", action=Pdb)

# pdb.set_trace on any hits
hunter.trace(F.module == "foo", F.function == "foobar", action=Pdb)

# pdb.set_trace when function is foobar, otherwise just print when module is foo
hunter.trace(F.module == "foo", When(F.function == "foobar", action=Pdb))

# dumping variables from stack
hunter.trace(When(F.function == "foobar", action=DumpVars(F.name == "foobar")), F.module == "foo")
hunter.trace(When(F.function == "foobar", action=DumpVars(F.name.in_(["foobar", "mumbojumbo"]))), F.module == "foo")

# multiple actions
hunter.trace(When(F.function == "foobar", actions=[DumpVars(F.name == "foobar"), Pdb]), F.module == "foo")

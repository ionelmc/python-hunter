# simple use
hunter.trace(function="foobar")

# "or" by expression
hunter.trace(module="foo", function="foobar")

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

# customization
hunter.trace(lambda module, function, locals: locals["node"] == "Foobar",
             module="foo", function="foobar")
hunter.trace(F(lambda module, function, locals: locals["node"] == "Foobar",
               function="foobar", actions=[DumpVars(name="foobar"), Pdb]), module="foo",)
hunter.trace(F(function="foobar", actions=[DumpVars(name="foobar"),
                                           lambda module, function, locals: print("some custom output")]), module="foo",)

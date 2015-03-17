def named(function=None, func=None, module=None, mod=None, filename=None):
    assert not function or not func, "Duplicate arguments, `func` is alias for `function`!"
    assert not module or not mod, "Duplicate arguments, `mod` is alias for `module`!"
    function = function or func
    module = module or mod

    def named_predicate(frame, kind, arg):
        if function:
            if function != frame.f_code.co_name:
                return

        if module:
            print(frame.f_globals['__name__'])
            if module != frame.f_globals.get('__name__', None):
                return

        if filename:
            if filename != frame.f_globals.get('__file__', None):
                return
        return True
    return named_predicate


def or_(*predicates):
    def or_predicate(frame, kind, arg):
        return any(list(  # build it all (``list()``) cause we want to perform all the actions
            predicate(frame, kind, arg) for predicate in predicates
        ))
    return or_predicate


def and_(*predicates):
    def and_predicate(frame, kind, arg):
        return all(
            predicate(frame, kind, arg) for predicate in predicates
        )
    return and_predicate

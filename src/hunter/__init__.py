import sys

from hunter.actions import CodePrinter, VarsDumper

__version__ = "0.1.0"


def trace(*predicates, **inlined):
    if "action" not in inlined:
        inlined["action"] = CodePrinter()
    predicate = F(*predicates, **inlined)

    def tracer(frame, kind, arg):
        if predicate(Event(frame, kind, arg)):
            return tracer

    sys.settrace(tracer)


def stop():
    sys.settrace(None)


class Tracer(object):
    pass


class CachedProperty(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls):
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class Event(object):
    def __init__(self, frame, kind, arg):
        self.frame = frame
        self.kind = kind
        self.arg = arg

    @CachedProperty
    def locals(self):
        return self.frame.f_locals

    @CachedProperty
    def globals(self):
        return self.frame.f_locals

    @CachedProperty
    def function(self):
        return self.frame.f_code.co_name

    @CachedProperty
    def module(self):
        return self.frame.f_globals.get('__name__', None)

    @CachedProperty
    def filename(self):
        return self.frame.f_globals.get('__file__', None)

    @CachedProperty
    def lineno(self):
        return self.frame.f_lineno

    __getitem__ = object.__getattribute__


class F(object):
    # def __new__(cls, *predicates, **query):
    #     if predicates

    def __init__(self, *predicates, **query):
        self.actions = query.pop("actions", [])
        if "action" in query:
            self.actions.append(query.pop("action"))
        for key in query:
            if key not in ('function', 'module', 'filename'):
                raise TypeError("Unexpected argument %r. Must be one of 'function', 'module' or 'filename'.")
        self.query = query
        self.predicates = predicates

    def __str__(self):
        return "F({}{}{}{}{})".format(
            ', '.join(str(p) for p in self.predicates),
            ', ' if self.predicates and self.query else '',
            ', '.join("{}={}".format(*item) for item in self.query.items()),
            ', ' if (self.predicates or self.query) and self.action else '',
            'action={}'.format(self.action),
        )

    def __call__(self, event):
        for predicate in self.predicates:
            if not predicate(event):
                return

        for key, value in self.query.items():
            if event[key] != value:
                return

        if self.actions:
            for action in self.actions:
                action(event)

        return True

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)


class And(object):
    def __init__(self, *predicates):
        self.predicates = predicates

    def __str__(self):
        return "And({})".format(', '.join(str(p) for p in self.predicates))

    def __call__(self, event):
        for predicate in self.predicates:
            if not predicate(event):
                return
        return True


class Or(object):
    def __init__(self, *predicates):
        self.predicates = predicates

    def __call__(self, event):
        for predicate in self.predicates:
            if predicate(event):
                return True


if __name__ == '__main__':
    trace(actions=[CodePrinter(), VarsDumper(names=['a', 'b'])])

    def foo(*x):
        #print(x)
        a = 1 + 2
        b = 3
        try:
            raise Exception('BOOM!')
        finally:
            return x

    foo(1, 2, 3)

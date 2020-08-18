import re
from array import array
from collections import OrderedDict
from collections import deque
from collections import namedtuple
from datetime import date
from datetime import datetime
from datetime import tzinfo
from decimal import Decimal
from socket import _socket
from socket import socket

import py
import six

from hunter.util import safe_repr

try:
    from inspect import getattr_static
except ImportError:
    from hunter.backports.inspect import getattr_static

MyTuple = namedtuple("MyTuple", "a b")


class Dict(dict):
    pass


class List(list):
    pass


class Set(set):
    pass


Stuff = namedtuple('Stuff', 'a b')


class Foobar(object):
    __slots__ = ()
    __repr__ = lambda _: "Foo-bar"


class Bad1:
    def __repr__(self):
        raise Exception("Bad!")

    def method(self):
        pass


class String(str):
    def __repr__(self):
        raise Exception("Bad!")

    __str__ = __repr__


class Int(int):
    def __repr__(self):
        raise Exception("Bad!")

    __str__ = __repr__


class TzInfo(tzinfo):
    def __repr__(self):
        raise Exception("Bad!")

    __str__ = __repr__


class Bad2(object):
    def __repr__(self):
        raise Exception("Bad!")

    def method(self):
        pass


def test_safe_repr():
    data = {
        'a': [set('b')],
        ('c',): deque(['d']),
        'e': _socket.socket(),
        1: array('d', [1, 2]),
        frozenset('f'): socket(),
        'g': Dict({
            'a': List('123'),
            'b': Set([Decimal('1.0')]),
            'c': Stuff(1, 2),
            'd': Exception(1, 2, {
                'a': safe_repr,
                'b': Foobar,
                'c': Bad2(),
                'ct': Bad2,
            })
        }),
        'od': OrderedDict({'a': 'b'}),
        'nt': MyTuple(1, 2),
        'bad1': Bad1().method,
        'bad2': Bad2().method,
        'regex': re.compile('123', 0),
        'badregex': re.compile(String('123')),
        'badregex2': re.compile(String('123'), Int(re.IGNORECASE)),
        'date': date(Int(2000), Int(1), Int(2)),
        'datetime': datetime(Int(2000), Int(1), Int(2), Int(3), Int(4), Int(5), Int(600), tzinfo=TzInfo()),
    }
    print(re.compile(String('123'), Int(re.IGNORECASE)).match('123'))
    print(safe_repr(data))
    print(safe_repr([data]))
    print(safe_repr([[data]]))
    print(safe_repr([[[data]]]))
    print(safe_repr([[[[data]]]]))
    print(safe_repr([[[[[data]]]]]))

    assert safe_repr(py.io).startswith('<py._vendored_packages.apipkg.ApiModule object at 0x')


def test_reliable_primitives():
    # establish a baseline for primitives that cannot be messed with descriptors and metaclasses
    side_effects = []

    class MetaMeta(type):
        @property
        def __mro__(self):
            side_effects.append('MetaMeta.__mro__')
            return [Meta, type]

        @property
        def __class__(self):
            side_effects.append('MetaMeta.__class__')
            return MetaMeta

        def __subclasscheck__(self, subclass):
            side_effects.append('MetaMeta.__subclasscheck__')
            return True

        def __instancecheck__(self, instance):
            side_effects.append('MetaMeta.__instancecheck__')
            return True

    class Meta(six.with_metaclass(MetaMeta, type)):
        @property
        def __mro__(self):
            side_effects.append('Meta.__mro__')
            return [Foobar, object]

        @property
        def __class__(self):
            side_effects.append('Meta.__class__')
            return Meta

        def __subclasscheck__(self, subclass):
            side_effects.append('Meta.__subclasscheck__')
            return True

        def __instancecheck__(self, instance):
            side_effects.append('Meta.__instancecheck__')
            return True

        @property
        def __dict__(self, _={}):
            side_effects.append('Meta.__dict__')
            return _

    class Foobar(six.with_metaclass(Meta, object)):
        @property
        def __mro__(self):
            side_effects.append('Foobar.__mro__')
            return ['?']

        @property
        def __class__(self):
            side_effects.append('Foobar.__class__')
            return Foobar

        def __subclasscheck__(self, subclass):
            side_effects.append('Foobar.__subclasscheck__')
            return True

        def __instancecheck__(self, instance):
            side_effects.append('Foobar.__instancecheck__')
            return True

        @property
        def __dict__(self):
            side_effects.append('Foobar.__dict__')
            return {}

    class SubFoobar(Foobar):
        pass

    class Plain(object):
        pass

    del side_effects[:]

    foo = Foobar()
    assert type(foo) is Foobar
    assert type(Foobar) is Meta
    assert type(foo) is Foobar
    assert Foobar.__bases__
    assert not side_effects
    isinstance(type(foo), dict)
    assert side_effects == ['Meta.__class__']

    isinstance(foo, dict)
    assert side_effects == ['Meta.__class__', 'Foobar.__class__']

    isinstance(1, Foobar)
    assert side_effects == ['Meta.__class__', 'Foobar.__class__', 'Meta.__instancecheck__']

    issubclass(type, Foobar)
    assert side_effects == ['Meta.__class__', 'Foobar.__class__', 'Meta.__instancecheck__', 'Meta.__subclasscheck__']

    assert Foobar.__mro__
    assert side_effects == ['Meta.__class__', 'Foobar.__class__', 'Meta.__instancecheck__', 'Meta.__subclasscheck__', 'Meta.__mro__']

    del side_effects[:]

    assert Meta.__mro__
    assert side_effects == ['MetaMeta.__mro__']

    assert getattr_static(Plain, '__mro__') is type.__dict__['__mro__']
    assert getattr_static(Foobar, '__mro__') is not type.__dict__['__mro__']
    assert side_effects == ['MetaMeta.__mro__']

    assert issubclass(SubFoobar, Foobar)
    assert side_effects == ['MetaMeta.__mro__', 'Meta.__subclasscheck__']

    subfoo = SubFoobar()
    assert isinstance(SubFoobar, Foobar)
    assert side_effects == ['MetaMeta.__mro__', 'Meta.__subclasscheck__', 'Meta.__instancecheck__']

    issubclass(type(SubFoobar()), Foobar)
    assert side_effects == ['MetaMeta.__mro__', 'Meta.__subclasscheck__', 'Meta.__instancecheck__', 'Meta.__subclasscheck__']

    del side_effects[:]

    isinstance(Foobar, dict)
    isinstance(type(Foobar), dict)
    isinstance(type(type(Foobar)), dict)
    issubclass(Plain, Foobar)
    issubclass(Plain, type(Foobar))
    issubclass(Plain, type(type(Foobar)))
    assert side_effects == ['Meta.__class__', 'MetaMeta.__class__', 'Meta.__subclasscheck__', 'MetaMeta.__subclasscheck__']

    del side_effects[:]

    issubclass(getattr_static(SubFoobar(), '__class__'), Foobar)
    assert side_effects[-1] == 'Meta.__subclasscheck__'

    del side_effects[:]

    getattr_static(type(SubFoobar()), '__instancecheck__')
    getattr_static(type(SubFoobar()), '__subclasscheck__')
    assert not side_effects

    safe_repr(Foobar())
    safe_repr(Foobar)
    assert not side_effects

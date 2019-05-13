import _socket
import socket
from array import array
from collections import deque
from collections import namedtuple
from decimal import Decimal

import py

from hunter.util import hasdict
from hunter.util import rudimentary_repr


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


class Bad:
    pass


def test_rudimentary_repr():
    data = {
        'a': [set('b')],
        ('c',): deque(['d']),
        'e': _socket.socket(),
        1: array('d', [1, 2]),
        frozenset('f'): socket.socket(),
        'g': Dict({
            'a': List('123'),
            'b': Set([Decimal('1.0')]),
            'c': Stuff(1, 2),
            'd': Exception(1, 2, {
                'a': rudimentary_repr,
                'b': Foobar,
                'c': Bad(),
                'ct': Bad,
            })
        }),

    }
    print(rudimentary_repr(data))
    print(rudimentary_repr([data]))
    print(rudimentary_repr([[data]]))
    print(rudimentary_repr([[[data]]]))
    print(rudimentary_repr([[[[data]]]]))
    print(rudimentary_repr([[[[[data]]]]]))


def test_hasutil():
    assert hasdict(type(py.io), py.io) is True
    sock, _ = socket.socketpair()
    assert hasdict(type(sock), sock) is False

    class Foo(object):
        pass

    assert hasdict(Foo, Foo()) is True

    class Bar:
        pass

    assert hasdict(Bar, Bar()) is True

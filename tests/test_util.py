from array import array
from collections import deque
from collections import namedtuple
from decimal import Decimal
from socket import _socket
from socket import socket

import py

from hunter.util import has_dict

try:
    from hunter._actions import safe_repr
except ImportError:
    from hunter.actions import safe_repr

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
        frozenset('f'): socket(),
        'g': Dict({
            'a': List('123'),
            'b': Set([Decimal('1.0')]),
            'c': Stuff(1, 2),
            'd': Exception(1, 2, {
                'a': safe_repr,
                'b': Foobar,
                'c': Bad(),
                'ct': Bad,
            })
        }),

    }
    print(safe_repr(data))
    print(safe_repr([data]))
    print(safe_repr([[data]]))
    print(safe_repr([[[data]]]))
    print(safe_repr([[[[data]]]]))
    print(safe_repr([[[[[data]]]]]))


def test_has_dict():
    assert has_dict(type(py.io), py.io) is True

    sock = socket()
    assert has_dict(type(sock), sock) is False

    class Foo(object):
        pass

    assert has_dict(Foo, Foo()) is True

    class Bar:
        pass

    assert has_dict(Bar, Bar()) is True

from __future__ import print_function

import sys

import pytest

import hunter
from hunter import And
from hunter import Backlog
from hunter import CallPrinter
from hunter import CodePrinter
from hunter import Debugger
from hunter import From
from hunter import Manhole
from hunter import Not
from hunter import Or
from hunter import Q
from hunter import Query
from hunter import When
from hunter import _Backlog
from hunter.actions import ColorStreamAction


class FakeCallable(object):
    def __init__(self, value):
        self.value = value

    def __call__(self):
        raise NotImplementedError('Nope')

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)


C = FakeCallable


@pytest.fixture
def mockevent():
    return hunter.Event(sys._getframe(0), 2 if '_event' in hunter.Event.__module__ else 'line', None, hunter.Tracer())


def test_no_inf_recursion(mockevent):
    assert Or(And(1)) == 1
    assert Or(Or(1)) == 1
    assert And(Or(1)) == 1
    assert And(And(1)) == 1
    predicate = Q(Q(lambda ev: 1, module='wat'))
    print('predicate:', predicate)
    predicate(mockevent)


def test_compression():
    assert Or(Or(1, 2), And(3)) == Or(1, 2, 3)
    assert Or(Or(1, 2), 3) == Or(1, 2, 3)
    assert Or(1, Or(2, 3), 4) == Or(1, 2, 3, 4)
    assert And(1, 2, Or(3, 4)).predicates == (1, 2, Or(3, 4))

    assert repr(Or(Or(1, 2), And(3))) == repr(Or(1, 2, 3))
    assert repr(Or(Or(1, 2), 3)) == repr(Or(1, 2, 3))
    assert repr(Or(1, Or(2, 3), 4)) == repr(Or(1, 2, 3, 4))


def test_from_kwargs_split():
    assert From(module=1, depth=2, depth_lt=3) == From(Query(module=1), Query(depth=2, depth_lt=3))
    assert repr(From(module=1, depth=2, depth_lt=3)).replace('<hunter._', '<hunter.') == (
        "<hunter.predicates.From: condition=<hunter.predicates.Query: query_eq=(('module', 1),)>, "
        "predicate=<hunter.predicates.Query: query_eq=(('depth', 2),) query_lt=(('depth', 3),)>, watermark=0>"
    )


def test_not(mockevent):
    assert Not(1).predicate == 1
    assert ~Or(1, 2) == Not(Or(1, 2))
    assert ~And(1, 2) == Not(And(1, 2))

    assert ~Not(1) == 1

    assert ~Query(module=1) | ~Query(module=2) == Not(And(Query(module=1), Query(module=2)))
    assert ~Query(module=1) & ~Query(module=2) == Not(Or(Query(module=1), Query(module=2)))

    assert ~Query(module=1) | Query(module=2) == Or(Not(Query(module=1)), Query(module=2))
    assert ~Query(module=1) & Query(module=2) == And(Not(Query(module=1)), Query(module=2))

    assert ~(Query(module=1) & Query(module=2)) == Not(And(Query(module=1), Query(module=2)))
    assert ~(Query(module=1) | Query(module=2)) == Not(Or(Query(module=1), Query(module=2)))

    assert repr(~Or(1, 2)) == repr(Not(Or(1, 2)))
    assert repr(~And(1, 2)) == repr(Not(And(1, 2)))

    assert repr(~Query(module=1) | ~Query(module=2)) == repr(Not(And(Query(module=1), Query(module=2))))
    assert repr(~Query(module=1) & ~Query(module=2)) == repr(Not(Or(Query(module=1), Query(module=2))))

    assert repr(~(Query(module=1) & Query(module=2))) == repr(Not(And(Query(module=1), Query(module=2))))
    assert repr(~(Query(module=1) | Query(module=2))) == repr(Not(Or(Query(module=1), Query(module=2))))

    assert Not(Q(module=__name__))(mockevent) is False


def test_query_allowed():
    pytest.raises(TypeError, Query, 1)
    pytest.raises(TypeError, Query, a=1)


def test_when_allowed():
    pytest.raises(TypeError, When, 1)


@pytest.mark.parametrize('expr,expected', [
    ({'module': __name__}, True),
    ({'module': __name__ + '.'}, False),
    ({'module_startswith': 'test'}, True),
    ({'module__startswith': 'test'}, True),
    ({'module_contains': 'test'}, True),
    ({'module_contains': 'foo'}, False),
    ({'module_endswith': 'foo'}, False),
    ({'module__endswith': __name__.split('_')[-1]}, True),
    ({'module_in': __name__}, True),
    ({'module': 'abcd'}, False),
    ({'module': ['abcd']}, False),
    ({'module_in': ['abcd']}, False),
    ({'module_in': ['a', __name__, 'd']}, True),
    ({'module': 'abcd'}, False),
    ({'module_startswith': ('abc', 'test')}, True),
    ({'module_startswith': {'abc', 'test'}}, True),
    ({'module_startswith': ['abc', 'test']}, True),
    ({'module_startswith': ('abc', 'test')}, True),
    ({'module_startswith': ('abc', 'test')}, True),
    ({'module_startswith': ('abc', 'xyz')}, False),
    ({'module_endswith': ('abc', __name__.split('_')[-1])}, True),
    ({'module_endswith': {'abc', __name__.split('_')[-1]}}, True),
    ({'module_endswith': ['abc', __name__.split('_')[-1]]}, True),
    ({'module_endswith': ('abc', 'xyz')}, False),
    ({'module': 'abc'}, False),
    ({'module_regex': r'(_|_.*)\b'}, False),
    ({'module_regex': r'.+_.+$'}, True),
    ({'module_regex': r'(test|test.*)\b'}, True),
    ({'calls_gte': 0}, True),
    ({'calls_gt': 0}, False),
    ({'calls_lte': 0}, True),
    ({'calls_lt': 0}, False),
    ({'calls_gte': 1}, False),
    ({'calls_gt': -1}, True),
    ({'calls_lte': -1}, False),
    ({'calls_lt': 1}, True),
])
def test_matching(expr, mockevent, expected):
    assert Query(**expr)(mockevent) == expected


@pytest.mark.parametrize('exc_type,expr', [
    (TypeError, {'module_1': 1}),
    (TypeError, {'module1': 1}),
    (ValueError, {'module_startswith': 1}),
    (ValueError, {'module_startswith': {1: 2}}),
    (ValueError, {'module_endswith': 1}),
    (ValueError, {'module_endswith': {1: 2}}),
    (TypeError, {'module_foo': 1}),
    (TypeError, {'module_a_b': 1}),
])
def test_bad_query(expr, exc_type):
    pytest.raises(exc_type, Query, **expr)


def test_when(mockevent):
    called = []
    assert When(Q(module='foo'), lambda ev: called.append(ev))(mockevent) is False
    assert called == []

    assert When(Q(module=__name__), lambda ev: called.append(ev))(mockevent) is True
    assert called == [mockevent]

    called = []
    assert Q(module=__name__, action=lambda ev: called.append(ev))(mockevent) is True
    assert called == [mockevent]

    called = [[], []]
    predicate = (
        Q(module=__name__, action=lambda ev: called[0].append(ev)) |
        Q(module='foo', action=lambda ev: called[1].append(ev))
    )
    assert predicate(mockevent) is True
    assert called == [[mockevent], []]

    assert predicate(mockevent) is True
    assert called == [[mockevent, mockevent], []]

    called = [[], []]
    predicate = (
        Q(module=__name__, action=lambda ev: called[0].append(ev)) &
        Q(function='mockevent', action=lambda ev: called[1].append(ev))
    )
    assert predicate(mockevent) is True
    assert called == [[mockevent], [mockevent]]


def test_from(mockevent):
    pytest.raises((AttributeError, TypeError), From(), 1)
    assert From()(mockevent) is True

    called = []
    assert From(Q(module='foo') | Q(module='bar'), lambda ev: called.append(ev))(mockevent) is False
    assert called == []

    assert From(Not(Q(module='foo') | Q(module='bar')), lambda ev: called.append(ev))(mockevent) is None
    assert called

    called = []
    assert From(Q(module=__name__), lambda ev: called.append(ev))(mockevent) is None
    assert called


def test_backlog(mockevent):
    assert Backlog(module=__name__)(mockevent) is True

    class Action(ColorStreamAction):
        called = []

        def __call__(self, event):
            self.called.append(event)

    assert Backlog(Q(module='foo') | Q(module='bar'), action=Action)(mockevent) is False
    assert Action.called == []

    backlog = Backlog(Not(Q(module='foo') | Q(module='bar')), action=Action)
    assert backlog(mockevent) is True
    assert backlog(mockevent) is True
    assert Action.called == []

    def predicate(ev, store=[]):
        store.append(1)
        return len(store) > 2

    backlog = Backlog(predicate, action=Action, stack=0)

    assert backlog(mockevent) is False
    assert backlog(mockevent) is False
    assert backlog(mockevent) is True
    assert len(Action.called) == 1


def test_backlog_action_setup():
    assert isinstance(Backlog(module=1).action, CallPrinter)
    assert isinstance(Backlog(module=1, action=CodePrinter).action, CodePrinter)

    class FakeAction(ColorStreamAction):
        pass

    assert isinstance(Backlog(module=1, action=FakeAction).action, FakeAction)


def test_and_or_kwargs():
    assert And(1, function=2) == And(1, Query(function=2))
    assert Or(1, function=2) == Or(1, Query(function=2))


def test_from_typeerror():
    pytest.raises(TypeError, From, 1, 2, kind=3)
    pytest.raises(TypeError, From, 1, function=2)
    pytest.raises(TypeError, From, junk=1)


def test_backlog_typeerror():
    pytest.raises(TypeError, Backlog)
    pytest.raises(TypeError, Backlog, junk=1)
    pytest.raises(TypeError, Backlog, action=1)
    pytest.raises(TypeError, Backlog, module=1, action=1)
    pytest.raises(TypeError, Backlog, module=1, action=type)


def test_backlog_filter():
    class MyAction(ColorStreamAction):
        def __eq__(self, other):
            return True

    assert Backlog(Q(), action=MyAction).filter(function=1) == _Backlog(condition=Q(), filter=Query(function=1), action=MyAction)
    assert Backlog(Q(), action=MyAction, filter=Q(module=1)).filter(function=2) == _Backlog(
        condition=Q(), filter=And(Query(module=1), Query(function=2)), action=MyAction)

    def blabla():
        pass

    assert Backlog(Q(), action=MyAction, filter=blabla).filter(function=1) == _Backlog(
        condition=Q(), filter=And(blabla, Query(function=1)), action=MyAction)
    assert Backlog(Q(), action=MyAction, filter=Q(module=1)).filter(blabla, function=2) == _Backlog(
        condition=Q(), filter=And(Query(module=1), blabla, Query(function=2)), action=MyAction)


def test_and(mockevent):
    assert And(C(1), C(2)) == And(C(1), C(2))
    assert Q(module=1) & Q(module=2) == And(Q(module=1), Q(module=2))
    assert Q(module=1) & Q(module=2) & Q(module=3) == And(Q(module=1), Q(module=2), Q(module=3))

    assert (Q(module=__name__) & Q(module='foo'))(mockevent) is False
    assert (Q(module=__name__) & Q(function='mockevent'))(mockevent) is True

    assert And(1, 2) | 3 == Or(And(1, 2), 3)


def test_or(mockevent):
    assert Q(module=1) | Q(module=2) == Or(Q(module=1), Q(module=2))
    assert Q(module=1) | Q(module=2) | Q(module=3) == Or(Q(module=1), Q(module=2), Q(module=3))

    assert (Q(module='foo') | Q(module='bar'))(mockevent) is False
    assert (Q(module='foo') | Q(module=__name__))(mockevent) is True

    assert Or(1, 2) & 3 == And(Or(1, 2), 3)


def test_str_repr():
    assert repr(Q(module='a', function='b')).endswith("predicates.Query: query_eq=(('function', 'b'), ('module', 'a'))>")
    assert str(Q(module='a', function='b')) == "Query(function='b', module='a')"

    assert repr(Q(module='a')).endswith("predicates.Query: query_eq=(('module', 'a'),)>")
    assert str(Q(module='a')) == "Query(module='a')"

    assert "predicates.When: condition=<hunter." in repr(Q(module='a', action=C('foo')))
    assert "predicates.Query: query_eq=(('module', 'a'),)>, actions=('foo',)>" in repr(Q(module='a', action=C('foo')))
    assert str(Q(module='a', action=C('foo'))) == "When(Query(module='a'), 'foo')"

    assert "predicates.Not: predicate=<hunter." in repr(~Q(module='a'))
    assert "predicates.Query: query_eq=(('module', 'a'),)>>" in repr(~Q(module='a'))
    assert str(~Q(module='a')) == "Not(Query(module='a'))"

    assert "predicates.Or: predicates=(<hunter." in repr(Q(module='a') | Q(module='b'))
    assert "predicates.Query: query_eq=(('module', 'a'),)>, " in repr(Q(module='a') | Q(module='b'))
    assert repr(Q(module='a') | Q(module='b')).endswith("predicates.Query: query_eq=(('module', 'b'),)>)>")
    assert str(Q(module='a') | Q(module='b')) == "Or(Query(module='a'), Query(module='b'))"

    assert "predicates.And: predicates=(<hunter." in repr(Q(module='a') & Q(module='b'))
    assert "predicates.Query: query_eq=(('module', 'a'),)>," in repr(Q(module='a') & Q(module='b'))
    assert repr(Q(module='a') & Q(module='b')).endswith("predicates.Query: query_eq=(('module', 'b'),)>)>")
    assert str(Q(module='a') & Q(module='b')) == "And(Query(module='a'), Query(module='b'))"

    assert repr(From(module='a', depth_lte=2)).replace('<hunter._', '<hunter.') == (
        "<hunter.predicates.From: condition=<hunter.predicates.Query: query_eq=(('module', 'a'),)>, "
        "predicate=<hunter.predicates.Query: query_lte=(('depth', 2),)>, watermark=0>"
    )
    assert str(From(module='a', depth_gte=2)) == "From(Query(module='a'), Query(depth_gte=2), watermark=0)"

    assert repr(Backlog(module='a', action=CodePrinter, size=2)).replace('<hunter._', '<hunter.').startswith(
        "<hunter.predicates.Backlog: condition=<hunter.predicates.Query: query_eq=(('module', 'a'),)>, "
        "size=2, stack=10, vars=False, action=CodePrinter"
    )

    assert repr(Debugger()) == "Debugger(klass=<class 'pdb.Pdb'>, kwargs={})"
    assert str(Debugger()) == "Debugger(klass=<class 'pdb.Pdb'>, kwargs={})"

    assert repr(Manhole()) == 'Manhole(options={})'
    assert str(Manhole()) == 'Manhole(options={})'


def test_q_deduplicate_callprinter():
    out = repr(Q(CallPrinter(), action=CallPrinter()))
    assert out.startswith('CallPrinter(')


def test_q_deduplicate_codeprinter():
    out = repr(Q(CodePrinter(), action=CodePrinter()))
    assert out.startswith('CodePrinter(')


def test_q_deduplicate_callprinter_cls():
    out = repr(Q(CallPrinter(), action=CallPrinter))
    assert out.startswith('CallPrinter(')


def test_q_deduplicate_codeprinter_cls():
    out = repr(Q(CodePrinter(), action=CodePrinter))
    assert out.startswith('CodePrinter(')


def test_q_deduplicate_callprinter_inverted():
    out = repr(Q(CallPrinter(), action=CodePrinter()))
    assert out.startswith('CallPrinter(')


def test_q_deduplicate_codeprinter_inverted():
    out = repr(Q(CodePrinter(), action=CallPrinter()))
    assert out.startswith('CodePrinter(')


def test_q_deduplicate_callprinter_cls_inverted():
    out = repr(Q(CallPrinter(), action=CodePrinter))
    assert out.startswith('CallPrinter(')


def test_q_deduplicate_codeprinter_cls_inverted():
    out = repr(Q(CodePrinter(), action=CallPrinter))
    assert out.startswith('CodePrinter(')


def test_q_action_callprinter():
    out = repr(Q(action=CallPrinter()))
    assert 'condition=<hunter.' in out
    assert 'actions=(CallPrinter' in out


def test_q_action_codeprinter():
    out = repr(Q(action=CodePrinter()))
    assert 'condition=<hunter.' in out
    assert 'actions=(CodePrinter' in out


def test_q_nest_1():
    assert repr(Q(Q(module='a'))).endswith("predicates.Query: query_eq=(('module', 'a'),)>")


def test_q_not_callable():
    exc = pytest.raises(TypeError, Q, 'foobar')
    assert exc.value.args == ("Predicate 'foobar' is not callable.",)


def test_q_expansion():
    assert Q(C(1), C(2), module=3) == And(C(1), C(2), Q(module=3))
    assert Q(C(1), C(2), module=3, action=C(4)) == When(And(C(1), C(2), Q(module=3)), C(4))
    assert Q(C(1), C(2), module=3, actions=[C(4), C(5)]) == When(And(C(1), C(2), Q(module=3)), C(4), C(5))

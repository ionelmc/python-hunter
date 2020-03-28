import os

import pytest

import hunter


@pytest.fixture(autouse=True)
def cleanup():
    hunter._default_trace_args = None
    hunter._default_config.clear()
    yield
    hunter._default_trace_args = None
    hunter._default_config.clear()


@pytest.mark.parametrize('config', [
    ('foobar', (('x',), {'y': 1}), {},
     '''Failed to load hunter config from PYTHONHUNTERCONFIG 'foobar': NameError'''),
    ('foobar=1', (('x',), {'y': 1}), {}, '''Discarded config from PYTHONHUNTERCONFIG foobar=1: '''),
    ('foobar=1, force_colors=1', (('x',), {'y': 1}), {'force_colors': 1},
     '''Discarded config from PYTHONHUNTERCONFIG foobar=1: '''),
    ('klass=123', (('x',), {'y': 1}), {'klass': 123}, ''),
    ('stream=123', (('x',), {'y': 1}), {'stream': 123}, ''),
    ('force_colors=123', (('x',), {'y': 1}), {'force_colors': 123}, ''),
    ('filename_alignment=123', (('x',), {'y': 1}), {'filename_alignment': 123}, ''),
    ('thread_alignment=123', (('x',), {'y': 1}), {'thread_alignment': 123}, ''),
    ('repr_limit=123', (('x',), {'y': 1}), {'repr_limit': 123}, ''),
    ('stdlib=0', (('x',), {'y': 1, 'stdlib': 0}), {}, ''),
    ('clear_env_var=1', (('x',), {'y': 1, 'clear_env_var': 1}), {}, ''),
    ('threading_support=1', (('x',), {'y': 1, 'threading_support': 1}), {}, ''),
    ('threads_support=1', (('x',), {'y': 1, 'threads_support': 1}), {}, ''),
    ('thread_support=1', (('x',), {'y': 1, 'thread_support': 1}), {}, ''),
    ('threadingsupport=1', (('x',), {'y': 1, 'threadingsupport': 1}), {}, ''),
    ('threadssupport=1', (('x',), {'y': 1, 'threadssupport': 1}), {}, ''),
    ('threadsupport=1', (('x',), {'y': 1, 'threadsupport': 1}), {}, ''),
    ('threading=1', (('x',), {'y': 1, 'threading': 1}), {}, ''),
    ('threads=1', (('x',), {'y': 1, 'threads': 1}), {}, ''),
    ('thread=1', (('x',), {'y': 1, 'thread': 1}), {}, ''),
    ('', (('x',), {'y': 1}), {}, ''),
], ids=lambda x: repr(x))
def test_config(monkeypatch, config, capsys):
    env, result, defaults, stderr = config
    monkeypatch.setitem(os.environ, 'PYTHONHUNTERCONFIG', env)
    hunter.load_config()
    assert hunter._apply_config(('x',), {'y': 1}) == result
    assert hunter._default_config == defaults
    output = capsys.readouterr()
    assert output.err.startswith(stderr)


def test_empty_config(monkeypatch, capsys):
    monkeypatch.setitem(os.environ, 'PYTHONHUNTERCONFIG', ' ')
    hunter.load_config()
    assert hunter._apply_config((), {}) == ((), {})
    assert hunter._default_config == {}
    output = capsys.readouterr()
    assert output.err == ''

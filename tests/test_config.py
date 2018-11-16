import os

import pytest

from hunter.config import DEFAULTS
from hunter.config import load_config


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
])
def test_config(monkeypatch, config, capsys):
    env, result, defaults, stderr = config
    monkeypatch.setitem(os.environ, 'PYTHONHUNTERCONFIG', env)
    assert load_config(('x',), {'y': 1}) == result
    assert DEFAULTS == defaults
    output = capsys.readouterr()
    assert output.err.startswith(stderr)

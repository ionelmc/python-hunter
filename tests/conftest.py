import sys

import pytest

from hunter.actions import CallPrinter


@pytest.fixture(autouse=True)
def cleanup_CallPrinter():
    CallPrinter.cleanup()


@pytest.fixture(autouse=True)
def cleanup_samples():
    for mod in list(sys.modules):
        if mod.startswith('sample'):
            del sys.modules[mod]

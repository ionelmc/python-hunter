import pytest

from hunter.actions import CallPrinter


@pytest.fixture(autouse=True)
def cleanup_CallPrinter():
    CallPrinter.cleanup()

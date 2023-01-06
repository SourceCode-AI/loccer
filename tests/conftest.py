import sys
import typing as t
from functools import partial
from unittest.mock import patch

import pytest

import loccer
from loccer.bases import Integration
from loccer.outputs.misc import InMemoryOutput


ORIGINAL_SYS_EXC_HOOK = sys.excepthook



class PyTestIntegration(Integration):
    NAME = "pytest"
    def __init__(self):
        self.data = {}

    def gather(self) -> t.Dict[str, t.Any]:
        return self.data.copy()


@pytest.fixture(autouse=True, scope="function")
def cleanup_hooks():
    global ORIGINAL_SYS_EXC_HOOK
    try:
        yield ORIGINAL_SYS_EXC_HOOK
    finally:
        sys.excepthook = ORIGINAL_SYS_EXC_HOOK


@pytest.fixture(scope="function")
def in_memory(cleanup_hooks):
    mem_out = InMemoryOutput()
    loccer.install(preserve_previous=False, output_handlers=(mem_out,))
    yield mem_out


@pytest.fixture(scope="function")
def integration():
    yield PyTestIntegration()


@pytest.fixture(scope="function", autouse=True)
def capture_override(in_memory, integration):
    hook = partial(loccer.excepthook, integrations=(integration,))
    lc = loccer.Loccer(handlers=(in_memory,), suppress_exception=True, exc_hook=hook)
    with patch.object(loccer, "capture_exception", new=lc):
        yield lc

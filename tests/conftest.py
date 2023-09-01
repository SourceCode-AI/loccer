import json
import sys
import typing as t
from functools import partial
from unittest.mock import patch

import pytest

import loccer
from loccer.bases import Integration, LoccerOutput
from loccer.outputs.misc import InMemoryOutput


ORIGINAL_SYS_EXC_HOOK = sys.excepthook



class PyTestIntegration(Integration):
    NAME = "pytest"
    def __init__(self):
        self.data = {}

    def gather(self, context: LoccerOutput) -> t.Dict[str, t.Any]:
        return self.data.copy()


@pytest.fixture(autouse=True, scope="function")
def cleanup_hooks():
    global ORIGINAL_SYS_EXC_HOOK
    try:
        yield ORIGINAL_SYS_EXC_HOOK
    finally:
        sys.excepthook = ORIGINAL_SYS_EXC_HOOK


@pytest.fixture(scope="function")
def in_memory(cleanup_hooks, integration):
    try:
        mem_out = InMemoryOutput()
        loccer.install(preserve_previous=False, output_handlers=(mem_out,), integrations=(integration,))
        yield mem_out
        for x in mem_out.logs:
            json.dumps(x)
    finally:
        loccer.restore()


@pytest.fixture(scope="function")
def integration():
    yield PyTestIntegration()


@pytest.fixture(scope="function", autouse=True)
def capture_override(in_memory, integration):
    hook = partial(loccer.excepthook)
    lc = loccer.Loccer(output_handlers=(in_memory,), integrations=(integration,), suppress_exception=True, exc_hook=hook)
    with patch.object(loccer, "capture_exception", new=lc):
        yield lc

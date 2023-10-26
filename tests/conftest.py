import json
import sys
import typing as t
from functools import partial
import uuid
from unittest.mock import patch

import pytest

import loccer
from loccer import JSONType
from loccer.bases import Integration, LoccerOutput, MetadataLog
from loccer.outputs.misc import InMemoryOutput


class PyTestIntegration(Integration):
    NAME = "pytest"

    def __init__(self):
        self.data = {}
        self.sess = None

    def gather(self, context: LoccerOutput) -> t.Dict[str, t.Any]:
        return self.data.copy()

    def session_data(self) -> JSONType:
        return self.sess


@pytest.fixture(autouse=True, scope="function")
def cleanup_hooks():
    try:
        yield sys.__excepthook__
    finally:
        sys.excepthook = sys.__excepthook__


@pytest.fixture(scope="function")
def lc(cleanup_hooks, integration):
    try:
        mem_out = InMemoryOutput()
        lc = loccer.install(preserve_previous=False, output_handlers=(mem_out,), integrations=(integration,))
        yield lc
    finally:
        loccer.restore()


@pytest.fixture(scope="function")
def in_memory(lc):
    mem_out = lc.output_handlers[0]
    yield mem_out
    for x in mem_out.logs:
        json.dumps(x)


@pytest.fixture(scope="function")
def integration():
    yield PyTestIntegration()


@pytest.fixture(scope="function", autouse=True)
def capture_override(in_memory, integration):
    hook = partial(loccer.excepthook)
    lc = loccer.Loccer(
        output_handlers=(in_memory,), integrations=(integration,), suppress_exception=True, exc_hook=hook
    )
    with patch.object(loccer, "capture_exception", new=lc):
        yield lc


@pytest.fixture(scope="session")
def log_sample():
    yield MetadataLog(str(uuid.uuid4()))

import uuid
from unittest.mock import patch

import loccer


def test_capture_exception_call(in_memory):
    assert in_memory.logs == []

    try:
        raise AssertionError("test_capture_exception_call")
    except AssertionError:
        loccer.capture_exception()

    assert len(in_memory.logs) == 1
    assert in_memory.logs[0]["exc_type"] == "AssertionError"
    assert in_memory.logs[0]["msg"] == "test_capture_exception_call"


def test_capture_exception_context_manager(in_memory):
    assert in_memory.logs == []

    with loccer.capture_exception:
        raise AssertionError("test_capture_exception_context_manager")


    assert len(in_memory.logs) == 1
    assert in_memory.logs[0]["exc_type"] == "AssertionError"
    assert in_memory.logs[0]["msg"] == "test_capture_exception_context_manager"


def test_capture_exception_decorator(in_memory):
    assert in_memory.logs == []

    @loccer.capture_exception
    def func():
        raise AssertionError("test_capture_exception_decorator")

    func()

    assert len(in_memory.logs) == 1
    assert in_memory.logs[0]["exc_type"] == "AssertionError"
    assert in_memory.logs[0]["msg"] == "test_capture_exception_decorator"


def test_basic_integration(integration, in_memory):
    val = str(uuid.uuid4())

    with patch.dict(integration.data) as m:
        integration.data["test_basic_integration"] = val

        with loccer.capture_exception:
            raise AssertionError("test_basic_integration")

    assert len(in_memory.logs) == 1
    log = in_memory.logs[0]
    assert log["exc_type"] == "AssertionError"
    assert log["msg"] == "test_basic_integration"

    assert integration.NAME in log["integrations"]
    assert log["integrations"][integration.NAME]["test_basic_integration"] == val, log["integrations"]


import asyncio
from unittest.mock import MagicMock, patch

import pytest

import loccer
from loccer.integrations.asyncio_context import AsyncioContextIntegration


@pytest.fixture(scope="function")
def asyncio_integration(in_memory):
    integration = AsyncioContextIntegration()
    assert integration._loop_ctx.name == "loop_ctx"
    prev = loccer.capture_exception.integrations[:]

    try:
        loccer.capture_exception.integrations = tuple(prev) + (integration,)
        yield integration
    finally:
        loccer.capture_exception.integrations = prev


@pytest.fixture(scope="module")
def loop():
    l = asyncio.new_event_loop()
    yield l


def test_asyncio_gather(loop):
    out = MagicMock()
    integration = AsyncioContextIntegration()
    data = integration.gather(out)
    # We are not running inside the async loop
    assert data is None

    async def _f():
        data = AsyncioContextIntegration.dump_coros()
        assert len(data) > 0
        return integration.gather(out)

    data = loop.run_until_complete(_f())
    print(data)
    assert "global_context" in data
    assert data["global_context"]
    assert data["coros"]
    for task_name, coro in data["coros"].items():
        assert isinstance(task_name, str)
        assert isinstance(coro["coro"], str)
        assert coro["is_done"] is False


def test_exception_handler(in_memory, asyncio_integration, loop):
    assert in_memory.logs == []
    ctx = {"message": "test_exception_handler"}
    loop.set_exception_handler(asyncio_integration.loop_exception_handler)
    loop.call_exception_handler(ctx)
    assert len(in_memory.logs) == 2
    log = in_memory.logs[1]
    assert log["data"]["msg"] == "Unknown exception in the asyncio loop"


def test_dump_coros(loop):
    data = AsyncioContextIntegration.dump_coros(loop)
    assert data == {}

    async def _f():
        orig_function = asyncio.all_tasks

        def _m(ev_loop):
            assert ev_loop is not None
            return orig_function(ev_loop)

        with patch("asyncio.all_tasks", new=_m):
            data = AsyncioContextIntegration.dump_coros()
        assert len(data) == 1

    loop.run_until_complete(_f())


def test_asyncio_enrichment_new_loop(in_memory, asyncio_integration, loop):
    assert in_memory.logs == []

    loop.set_exception_handler(asyncio_integration.loop_exception_handler)
    ev = asyncio.Event()

    async def _exc():
        try:
            raise RuntimeError("Test exception")
        finally:
            ev.set()

    try:
        loop.create_task(_exc())
        loop.run_until_complete(ev.wait())
    finally:
        loop.close()

    assert len(in_memory.logs) == 2

    log = in_memory.logs[1]
    assert log["exc_type"] == "RuntimeError"
    assert log["msg"] == "Test exception"

    assert "asyncio" in log["integrations"]
    data = log["integrations"]["asyncio"]
    assert len(data["coros"]) > 0
    assert data["loop_context"]["message"] == "'Task exception was never retrieved'"
    assert data["loop_context"]["exception"] == "RuntimeError('Test exception')"
    assert "_exc()" in data["loop_context"]["future"]

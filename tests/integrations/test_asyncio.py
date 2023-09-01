import asyncio

import pytest

import loccer
from loccer.integrations.asyncio_context import AsyncioContextIntegration


@pytest.fixture(scope="function")
def asyncio_integration(in_memory):
    integration = AsyncioContextIntegration()
    prev = loccer.capture_exception.integrations[:]

    try:
        loccer.capture_exception.integrations = tuple(prev) + (integration,)
        yield integration
    finally:
        loccer.capture_exception.integrations = prev


def test_asyncio_enrichment_new_loop(in_memory, asyncio_integration):
    assert in_memory.logs == []

    loop = asyncio.get_event_loop()
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

    assert len(in_memory.logs) == 1

    log = in_memory.logs[0]
    assert log["exc_type"] == "RuntimeError"
    assert log["msg"] == "Test exception"

    assert "asyncio" in log["integrations"]
    data = log["integrations"]["asyncio"]
    assert len(data["coros"]) > 0
    assert data["loop_context"]["message"] == "'Task exception was never retrieved'"
    assert data["loop_context"]["exception"] == "RuntimeError('Test exception')"
    assert "_exc()" in data["loop_context"]["future"]

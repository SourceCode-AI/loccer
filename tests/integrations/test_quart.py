import pytest

import loccer


quart = pytest.importorskip("quart")
from loccer.integrations.quart_context import QuartContextIntegration


quart_integration = QuartContextIntegration(capture_body=True, capture_4xx=True, capture_5xx=True)
app = quart.Quart(__name__)
app.testing = True
quart_integration.init_app(app)

@app.route("/")
async def index() -> str:
    return "Hello world"


@app.route("/status_code/<int:status_code>/<msg>", methods=["GET", "POST"])
async def status_code(status_code: int, msg: str) -> quart.Response:
    return quart.Response(msg, status=status_code)


@app.route("/exc")
async def throw_exc():
    raise ValueError("ratatata")


@pytest.fixture(scope="function")
def client(in_memory):
    assert quart.signals_available is True

    prev_integrations = loccer.capture_exception.integrations[:]
    try:
        loccer.capture_exception.integrations = tuple(prev_integrations) + (quart_integration,)
        yield app.test_client()
    finally:
        loccer.capture_exception.integrations = prev_integrations


@pytest.mark.asyncio
async def test_quart_hooks(client):
    req_fin = False

    async def req_fin_cb(sender, response, **extra):
        nonlocal req_fin
        req_fin = True


    quart.request_finished.connect(req_fin_cb)

    resp = await client.get("/")
    assert (await resp.data) == b"Hello world"
    assert resp.status_code == 200
    assert req_fin is True



@pytest.mark.asyncio
async def test_quart_enrichment(in_memory, client):
    assert in_memory.logs == []

    resp = await client.post(
        "/status_code/500/error_500",
        json={"test": "body"}
    )
    assert resp.status_code == 500
    assert b"error_500" in (await resp.data)

    assert len(in_memory.logs) == 1
    log = in_memory.logs[0]
    assert log["loccer_type"] == "metadata_log"
    assert log["data"]["msg"] == "Quart `500` response"
    assert log["data"]["status_code"] == 500
    extra = log["integrations"]["quart"]
    assert extra["quart_context"] is True
    assert extra["client_ip"] == "<local>"
    assert extra["url"] == "/status_code/500/error_500"
    assert extra["is_json"] is True
    assert extra["method"] == "POST"


@pytest.mark.parametrize("code, text", (
    (200, "ok"),
    (302, "ratata")
))
@pytest.mark.asyncio
async def test_success(code, text, in_memory, client):
    assert in_memory.logs == []
    resp = await client.get(f"/status_code/{code}/{text}")
    assert resp.status_code == code
    assert (await resp.data).decode() == text
    assert in_memory.logs == []

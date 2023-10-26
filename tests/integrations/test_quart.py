import importlib.metadata
from unittest.mock import patch, MagicMock

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

    client.set_cookie("localhost", "test_cookie", "test_value")

    resp = await client.post("/status_code/500/error_500", json={"test": "body"}, headers={"User-Agent": "pytest"})
    assert resp.status_code == 500
    assert b"error_500" in (await resp.data)

    assert len(in_memory.logs) == 2
    log = in_memory.logs[1]
    assert log["loccer_type"] == "metadata_log"
    assert log["data"]["msg"] == "Quart `500` response"
    assert log["data"]["status_code"] == 500
    extra = log["integrations"]["quart"]
    assert extra["quart_context"] is True
    assert extra["quart_version"] == importlib.metadata.version("quart")
    assert extra["client_ip"] == "<local>"
    assert extra["url"] == "/status_code/500/error_500"
    assert extra["is_json"] is True
    assert extra["content_type"] == "application/json"
    assert "content_length" in extra
    assert extra["method"] == "POST"
    assert extra["endpoint"] == "status_code"
    assert extra["cookies"] == {"test_cookie": "test_value"}
    assert isinstance(extra["headers"], dict)
    assert isinstance(extra["headers"]["Cookie"], str)
    assert extra["user_agent"] == "pytest"


@pytest.mark.parametrize("code, text", ((200, "ok"), (302, "ratata")))
@pytest.mark.asyncio
async def test_success(code, text, in_memory, client):
    assert in_memory.logs == []
    resp = await client.get(f"/status_code/{code}/{text}")
    assert resp.status_code == code
    assert (await resp.data).decode() == text
    assert in_memory.logs == []


def test_defaults():
    qapp = quart.Quart(__name__)
    qapp.config["PROPAGATE_EXCEPTIONS"] = True
    orig_exc_handler = qapp.log_exception
    qint = QuartContextIntegration()
    qint.init_app(qapp)
    assert qint.capture_4xx is False
    assert qint.capture_5xx is True
    assert qint.capture_body is False
    assert qint.original_exc_handler == orig_exc_handler
    assert qapp.log_exception != orig_exc_handler
    assert qapp.config["PROPAGATE_EXCEPTIONS"] is False
    assert callable(qapp.log_exception)


def test_no_quart(lc, log_sample):
    data = quart_integration.gather(log_sample)
    assert data == {"quart_context": False}
    assert quart_integration.session_data() is None

    qint = QuartContextIntegration()
    qapp = quart.Quart(__name__)
    with patch.object(quart, "signals_available", new=False):
        with pytest.warns(
            UserWarning, match=r"^Signals in Quart are not available \(`blinker` is probably not installed\)$"
        ):
            qint.init_app(qapp)


@pytest.mark.parametrize(
    "cap_4,cap_5,code,error",
    (
        (True, True, 399, False),
        (True, True, 400, True),
        (True, True, 401, True),
        (False, True, 400, False),
        (False, False, 400, False),
        (False, True, 499, False),
        (False, True, 500, True),
        (False, True, 501, True),
        (False, False, 500, False),
    ),
)
@pytest.mark.asyncio
async def test_capture_options(cap_4, cap_5, code, error, client, in_memory):
    with patch.object(quart_integration, "capture_4xx", new=cap_4), patch.object(
        quart_integration, "capture_5xx", new=cap_5
    ):
        assert in_memory.logs == []
        resp = await client.post(f"/status_code/{code}/ratatata")
        assert resp.status_code == code

        if error:
            assert len(in_memory.logs) > 0
        else:
            assert in_memory.logs == []


def test_exc_handler_patch():
    arg = object()
    kw = object()

    m = MagicMock()
    with (
        patch("loccer.integrations.quart_context.get_hybrid_context") as hcm,
        patch("sys.exc_info") as exc_info_m
    ):
        exc_info_m.return_value = (42,)*3
        QuartContextIntegration.exc_handler_patch(arg, original=m, kw=kw)
        m.assert_called_once_with(arg, kw=kw)
        hcm.assert_called_once()

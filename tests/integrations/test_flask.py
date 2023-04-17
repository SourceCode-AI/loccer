import pytest

import loccer


flask = pytest.importorskip("flask")
from loccer.integrations.flask_context import FlaskContextIntegration


flask_integration = FlaskContextIntegration(capture_body=True, capture_4xx=True, capture_5xx=True)
app = flask.Flask(__name__)
app.config["TESTING"] = True
flask_integration.init_app(app)


@app.route("/status_code/<int:status_code>/<msg>", methods=["GET", "POST"])
def status_code(status_code: int, msg: str) -> flask.Response:
    return flask.Response(msg, status=status_code)


@app.route("/exc")
def throw_exc():
    raise ValueError("ratatata")


@pytest.fixture(scope="function")
def client(in_memory):
    assert flask.signals_available is True

    prev_integrations = loccer.capture_exception.integrations[:]
    try:
        loccer.capture_exception.integrations = tuple(prev_integrations) + (flask_integration,)
        yield app.test_client()
    finally:
        loccer.capture_exception.integrations = prev_integrations


def test_flask_enrichment(in_memory, client):
    assert in_memory.logs == []

    resp = client.post(
        "/status_code/500/error_500",
        json={"test": "body"}
    )
    assert resp.status_code == 500, resp.text
    assert resp.text == "error_500"

    assert len(in_memory.logs) == 1
    log = in_memory.logs[0]
    assert log["loccer_type"] == "metadata_log"
    assert log["data"]["msg"] == "Flask `500` response"
    assert log["data"]["status_code"] == 500
    extra = log["integrations"]["flask"]
    assert extra["flask_context"] is True
    assert extra["client_ip"] == "127.0.0.1"
    assert extra["url"] == "/status_code/500/error_500"
    assert extra["json_payload"] == {"test": "body"}
    assert extra["is_json"] is True
    assert extra["method"] == "POST"


def test_flask_exception(in_memory, client):
    assert in_memory.logs == []

    with pytest.raises(ValueError):
        client.get("/exc")

    assert len(in_memory.logs) == 1
    log = in_memory.logs[0]
    assert log["loccer_type"] == "exception"
    assert log["integrations"]["flask"]["flask_context"] is True


@pytest.mark.parametrize("code, text", (
    (200, "ok"),
    (302, "ratata")
))
def test_success(code, text, in_memory, client):
    assert in_memory.logs == []
    resp = client.get(f"/status_code/{code}/{text}")
    assert resp.status_code == code
    assert resp.text == text
    assert in_memory.logs == []

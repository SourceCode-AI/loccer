import io
from unittest.mock import patch

import pytest

import loccer


flask = pytest.importorskip("flask")
from loccer.integrations.flask_context import FlaskContextIntegration


flask_integration = FlaskContextIntegration(capture_body=True, capture_4xx=True, capture_5xx=True)
app = None


def status_code(status_code: int, msg: str) -> flask.Response:
    return flask.Response(msg, status=status_code)


def throw_exc():
    raise ValueError("ratatata")


@pytest.fixture(scope="function", autouse=True)
def prepare_env():
    global app
    try:
        app = flask.Flask(__name__)
        app.config["TESTING"] = True

        app.route("/status_code/<int:status_code>/<msg>", methods=["GET", "POST"])(status_code)
        app.route("/exc", methods=["GET", "POST"])(throw_exc)
        flask_integration.init_app(app)
        yield app
    finally:
        flask.got_request_exception.receivers.clear()
        flask.request_finished.receivers.clear()
        app = None


@pytest.fixture(scope="function")
def client(in_memory, lc, prepare_env):
    prev_integrations = loccer.capture_exception.integrations[:]
    try:
        loccer.capture_exception.integrations = tuple(prev_integrations) + (flask_integration,)
        lc.session.captured = True
        yield prepare_env.test_client()
    finally:
        loccer.capture_exception.integrations = prev_integrations


def test_flask_defaults():
    f = FlaskContextIntegration()
    assert f.capture_4xx is False
    assert f.capture_5xx is True
    assert f.capture_body is False


def test_flask_enrichment(in_memory, client):
    assert in_memory.logs == []

    resp = client.post("/status_code/500/error_500", json={"test": "body"}, headers={"User-Agent": "pytest"})
    assert resp.status_code == 500, resp.text
    assert resp.text == "error_500"

    assert len(in_memory.logs) == 2
    log = in_memory.logs[1]
    assert log["loccer_type"] == "metadata_log"
    assert log["data"]["msg"] == "Flask `500` response"
    assert log["data"]["status_code"] == 500
    extra = log["integrations"]["flask"]
    assert extra["flask_context"] is True
    assert extra["client_ip"] == "127.0.0.1"
    assert extra["endpoint"] == "status_code"
    assert extra["url"] == "/status_code/500/error_500"
    assert extra["json_payload"] == {"test": "body"}
    assert "raw_payload" not in extra
    assert extra["is_json"] is True
    assert extra["method"] == "POST"
    assert extra["user_agent"] == "pytest"


def test_flask_exception(in_memory, client):
    assert in_memory.logs == []

    client.set_cookie("test_cookie", "test_value")

    with pytest.raises(ValueError):
        client.post("/exc", data="not a valid json", content_type="application/json")

    assert len(in_memory.logs) == 2
    log = in_memory.logs[1]
    assert log["loccer_type"] == "exception"
    fdata = log["integrations"]["flask"]
    assert fdata["flask_context"] is True
    assert fdata["flask_version"]
    assert fdata["endpoint"] == "throw_exc"
    assert fdata["client_ip"]
    assert fdata["url"]
    assert fdata["method"] == "POST"
    assert isinstance(fdata["headers"], dict)
    assert isinstance(fdata["user_agent"], str)
    assert fdata["is_json"] is True
    assert isinstance(fdata["form"], dict)
    assert fdata["content_length"] > 0
    assert fdata["content_type"] == "application/json"
    assert isinstance(fdata["files"], dict)
    assert fdata["json_payload"] is None
    assert fdata["raw_payload"] == "not a valid json"
    assert isinstance(fdata["cookies"], dict)
    assert fdata["cookies"]["test_cookie"] == "test_value"


@pytest.mark.parametrize("code, text", ((200, "ok"), (302, "ratata")))
def test_success(code, text, in_memory, client):
    assert in_memory.logs == []
    resp = client.get(f"/status_code/{code}/{text}")
    assert resp.status_code == code
    assert resp.text == text
    assert in_memory.logs == []


@pytest.mark.parametrize(
    "cap_4,cap_5,code,error",
    (
        (True, True, 399, False),
        (True, True, 400, True),
        (True, True, 401, True),
        (False, True, 400, False),
        (False, True, 499, False),
        (False, True, 500, True),
        (False, False, 500, False),
        (False, True, 501, True),
    ),
)
def test_capture_options(cap_4, cap_5, code, error: bool, client, in_memory):
    with patch.object(flask_integration, "capture_4xx", new=cap_4), patch.object(
        flask_integration, "capture_5xx", new=cap_5
    ):
        assert in_memory.logs == []
        resp = client.post(f"/status_code/{code}/ratatata")
        assert resp.status_code == code

        if error:
            assert len(in_memory.logs) > 0
        else:
            assert in_memory.logs == []


def test_file_upload(client, in_memory):
    file_content = b"test_file_content"
    fname = "test_file_name.exe.jpg.pdf.whatever"
    payload = {"test_file": (io.BytesIO(file_content), fname), "form_field": "form_value"}
    resp = client.post("/status_code/500/ratata", data=payload, content_type="multipart/form-data")
    assert resp.status_code == 500
    log = in_memory.logs[1]
    flog = log["integrations"]["flask"]
    assert len(flog["files"]) > 0
    assert flog["form"] == {"form_field": "form_value"}
    ffile = flog["files"]["test_file"]
    assert ffile["filename"] == fname
    assert ffile["form_name"] == "test_file"
    assert ffile["content_type"] == "application/octet-stream"
    assert ffile["content_length"] >= 0
    assert isinstance(ffile["headers"], dict)


def test_no_quart(lc, log_sample):
    data = flask_integration.gather(log_sample)
    assert data == {"flask_context": False}
    assert flask_integration.session_data() is None

    qint = FlaskContextIntegration()
    qapp = flask.Flask(__name__)
    with patch.object(flask, "signals_available", new=False, create=True):
        with pytest.warns(
            UserWarning, match=r"^Signals in Flask are not available \(`blinker` is probably not installed\)$"
        ):
            qint.init_app(qapp)

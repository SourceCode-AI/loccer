import warnings

import flask
from werkzeug.exceptions import HTTPException

from .. import get_hybrid_context
from ..bases import Integration, LoccerOutput, JSONType


class FlaskContextIntegration(Integration):
    """
    Flask integration for loccer
    """
    NAME = "flask"

    def __init__(
        self, *,
        capture_4xx: bool=False,
        capture_5xx: bool=True,
        capture_body: bool=False
    ):
        self.capture_4xx = capture_4xx
        self.capture_5xx = capture_5xx
        self.capture_body = capture_body

    def gather(self, context: LoccerOutput) -> JSONType:
        data: JSONType = {}
        if flask.request:
            data.update({
                "flask_context": True,
                "flask_version": flask.__version__,
                "endpoint": (flask.request.endpoint or "<unknown>"),
                "client_ip": flask.request.remote_addr,
                "url": flask.request.path,
                "method": flask.request.method,
                "headers": dict(flask.request.headers),
                "user_agent": flask.request.headers.get("User-Agent", "<unknown>"),
                "is_json": flask.request.is_json,
                "form": dict(flask.request.form),
                "content_length": flask.request.content_length,
                "content_type": flask.request.content_type,
                "files": {}
            })

            for fname, f in flask.request.files.items():
                fdata = {
                    "filename": f.filename,
                    "form_name": f.name,
                    "content_type": f.content_type,
                    "content_length": f.content_length,
                    "headers": dict(f.headers)
                }
                data["files"][fname] = fdata

            data["cookies"] = {
                k: v[0] if isinstance(v, list) and len(v) == 1 else v
                for k, v in flask.request.cookies.items()
            }

            if self.capture_body:
                try:
                    data["raw_payload"] = flask.request.get_data(as_text=True)
                except Exception:
                    data["raw_payload"] = "Loccer N/A; error getting raw request data"

        else:
            data["flask_context"] = False
        return data

    def init_app(self, flask_app: flask.Flask) -> None:
        if not flask.signals_available:
            warnings.warn("Signals in Flask are not available (`blinker` is probably not installed)")
        else:
            flask.got_request_exception.connect(self.handle_flask_exception)

            if self.capture_5xx or self.capture_4xx:
                flask.request_finished.connect(self.handle_request_end)

    def handle_request_end(self, sender, response, **extra):
        code = response.status_code
        if code < 400:
            return
        elif 400 <= code < 500 and not self.capture_4xx:
            return
        elif code >= 500 and not self.capture_5xx:
            return

        lc = get_hybrid_context()
        lc.log_metadata({
            "msg": f"Flask `{code}` response",
            "status_code": code,
        })

    def handle_flask_exception(self, sender, exception: Exception):
        get_hybrid_context().from_exception(exception)


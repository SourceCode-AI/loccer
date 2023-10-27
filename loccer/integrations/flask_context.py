import importlib.metadata
import typing
import warnings
import typing as t

import flask

from .. import get_hybrid_context
from ..bases import Integration, LoccerOutput, JSONType


class T_File(typing.TypedDict):
    filename: t.Optional[str]
    form_name: t.Optional[str]
    content_type: str
    content_length: int
    headers: dict[str, str]


class T_Flask(typing.TypedDict, total=False):  # pragma: no mutate
    flask_context: bool
    flask_version: str
    endpoint: str
    client_ip: t.Optional[str]
    url: str
    method: str
    headers: dict[str, str]
    user_agent: str
    is_json: bool
    form: dict[str, JSONType]
    content_length: t.Optional[int]
    content_type: str
    files: dict[str, T_File]
    cookies: dict[str, str]
    json_payload: JSONType
    raw_payload: str


class FlaskContextIntegration(Integration):
    """
    Flask integration for loccer
    """

    NAME = "flask"

    def __init__(
        self,
        *,
        capture_4xx: bool = False,
        capture_5xx: bool = True,
        capture_body: bool = False,
    ):
        self.capture_4xx = capture_4xx
        self.capture_5xx = capture_5xx
        self.capture_body = capture_body

    def gather(self, context: LoccerOutput) -> JSONType:
        data: T_Flask = {}
        if flask.request:
            data.update(
                {
                    "flask_context": True,
                    "flask_version": importlib.metadata.version("flask"),
                    "endpoint": (flask.request.endpoint or "<unknown>"),  # pragma: no mutate
                    "client_ip": flask.request.remote_addr,
                    "url": flask.request.path,
                    "method": flask.request.method,
                    "headers": dict(flask.request.headers),
                    "user_agent": flask.request.headers.get("User-Agent", "<unknown>"),  # pragma: no mutate
                    "is_json": flask.request.is_json,
                    "form": dict(flask.request.form),
                    "content_length": flask.request.content_length,
                    "content_type": flask.request.content_type,
                }
            )

            flask_files: dict[str, T_File] = {}

            for fname, f in flask.request.files.items():
                fdata: T_File = {
                    "filename": f.filename,
                    "form_name": f.name,
                    "content_type": f.content_type,
                    "content_length": f.content_length,
                    "headers": dict(f.headers),
                }
                flask_files[fname] = fdata

            data["files"] = flask_files
            data["cookies"] = {}

            for k, v in flask.request.cookies.items():
                if isinstance(v, list) and len(v) == 1:  # pragma: no mutate
                    v = v[0]  # pragma: no mutate

                data["cookies"][k] = v

            if self.capture_body:
                if flask.request.is_json:
                    data["json_payload"] = flask.request.get_json(silent=True)
                else:
                    data["json_payload"] = None  # pragma: no mutate

                if not data["json_payload"]:
                    try:
                        data["raw_payload"] = flask.request.get_data(as_text=True)
                    except Exception:
                        data["raw_payload"] = "Loccer N/A; error getting raw request data"  # pragma: no mutate

        else:
            return {"flask_context": False}
        return t.cast(JSONType, data)

    def session_data(self) -> JSONType:
        return None

    def init_app(self, flask_app: flask.Flask) -> None:
        if not getattr(flask, "signals_available", True):  # pragma: no mutate
            warnings.warn(UserWarning("Signals in Flask are not available (`blinker` is probably not installed)"))

        flask.got_request_exception.connect(self.handle_flask_exception)

        if self.capture_5xx or self.capture_4xx:  # pragma: no mutate
            flask.request_finished.connect(self.handle_request_end)

    def handle_request_end(self, sender: t.Any, response: flask.Response, **extra: t.Any) -> None:
        code = response.status_code
        if code < 400:
            return
        elif 400 <= code < 500 and not self.capture_4xx:
            return
        elif code >= 500 and not self.capture_5xx:
            return

        lc = get_hybrid_context()
        lc.log_metadata(
            {
                "msg": f"Flask `{code}` response",
                "status_code": code,
            }
        )

    def handle_flask_exception(self, sende: t.Any, exception: Exception, **kwargs: t.Any) -> None:
        get_hybrid_context().from_exception(exception)

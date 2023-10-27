import functools
import importlib.metadata
import sys
import warnings
import typing as t

import quart

from .. import get_hybrid_context
from ..bases import Integration, LoccerOutput
from ..ltypes import JSONType, T, U, V, T_exc, T_exc_tb, TracebackType


class T_Quart(t.TypedDict, total=False):  # pragma: no mutate
    quart_context: bool
    quart_version: str
    endpoint: str
    client_ip: t.Optional[str]
    url: str
    method: str
    headers: dict[str, str]
    user_agent: str
    is_json: bool
    content_length: t.Optional[int]
    content_type: str
    cookies: dict[str, t.Union[list[str], str]]


T_qhandler = t.Callable[
    [t.Union[tuple[type, BaseException, TracebackType], tuple[None, None, None]]], None
]  # pragma: no mutate


class QuartContextIntegration(Integration):
    """
    Quart integration for loccer
    """

    NAME = "quart"

    def __init__(
        self,
        *,
        capture_4xx: bool = False,
        capture_5xx: bool = True,
        capture_body: bool = False,
    ) -> None:
        self.capture_4xx = capture_4xx
        self.capture_5xx = capture_5xx
        self.capture_body = capture_body

    def gather(self, context: LoccerOutput) -> JSONType:
        data: T_Quart = {}
        if quart.request:
            cookies: dict[str, t.Union[list[str], str]] = {}
            data.update(
                {
                    "quart_context": True,
                    "quart_version": importlib.metadata.version("quart"),
                    "endpoint": (quart.request.endpoint or "<unknown>"),  # pragma: no mutate
                    "client_ip": quart.request.remote_addr,
                    "url": quart.request.path,
                    "method": quart.request.method,
                    "headers": dict(quart.request.headers),
                    "user_agent": quart.request.headers.get("User-Agent", "<unknown>"),  # pragma: no mutate
                    "is_json": quart.request.is_json,
                    "content_length": quart.request.content_length,
                    "content_type": quart.request.content_type,
                    "cookies": cookies,
                }
            )

            for k, v in quart.request.cookies.items():
                if isinstance(v, list) and len(v) == 1:  # pragma: no mutate
                    v = v[0]  # pragma: no mutate

                cookies[k] = v
        else:
            data["quart_context"] = False
        return t.cast(JSONType, data)

    def session_data(self) -> JSONType:
        return None

    def init_app(self, quart_app: quart.Quart) -> None:
        quart_app.config["PROPAGATE_EXCEPTIONS"] = False
        original_exc_handler = quart_app.log_exception

        def _log_exception(
            exception_info: t.Union[tuple[type, BaseException, TracebackType], tuple[None, None, None]]
        ) -> None:
            if (exc := exception_info[1]) is not None:
                get_hybrid_context().from_exception(exc)

            return original_exc_handler(exception_info)

        quart_app.log_exception = _log_exception

        if not getattr(quart, "signals_available", True):  # pragma: no mutate
            warnings.warn(UserWarning("Signals in Quart are not available (`blinker` is probably not installed)"))
        else:
            # FIXME: quart.got_request_exception.connect(self.handle_quart_exception)

            if self.capture_5xx or self.capture_4xx:  # pragma: no mutate
                quart.request_finished.connect(self.handle_request_end)

    async def handle_request_end(self, sender: t.Any, response: quart.Response, **extra: t.Any) -> None:
        code: int = response.status_code
        if code < 400:
            return
        elif 400 <= code < 500 and not self.capture_4xx:
            return
        elif code >= 500 and not self.capture_5xx:
            return

        lc = get_hybrid_context()
        lc.log_metadata(
            {
                "msg": f"Quart `{code}` response",
                "status_code": code,
            }
        )

    @staticmethod  # pragma: no mutate
    async def handle_quart_exception(sender: t.Any, exception: Exception, **extra: t.Any) -> None:
        get_hybrid_context().from_exception(exception)

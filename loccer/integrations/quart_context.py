import functools
import sys
import warnings

import quart

from .. import get_hybrid_context
from ..bases import Integration, LoccerOutput, JSONType


class QuartContextIntegration(Integration):
    """
    Quart integration for loccer
    """
    NAME = "quart"

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
        if quart.request:
            data.update({
                "quart_context": True,
                # FIXME "quart_version": quart.__version__,
                "endpoint": (quart.request.endpoint or "<unknown>"),
                "client_ip": quart.request.remote_addr,
                "url": quart.request.path,
                "method": quart.request.method,
                "headers": dict(quart.request.headers),
                "user_agent": quart.request.headers.get("User-Agent", "<unknown>"),
                "is_json": quart.request.is_json,
                "content_length": quart.request.content_length,
                "content_type": quart.request.content_type,
                "files": {}
            })

            data["cookies"] = {
                k: v[0] if isinstance(v, list) and len(v) == 1 else v
                for k, v in quart.request.cookies.items()
            }
        else:
            data["quart_context"] = False
        return data

    def init_app(self, quart_app: quart.Quart) -> None:
        original_exc_handler = quart_app.log_exception
        quart_app.log_exception = functools.partial(self.exc_handler_patch, original=original_exc_handler)

        if not quart.signals_available:
            warnings.warn("Signals in Quart are not available (`blinker` is probably not installed)")
        else:
            # FIXME: quart.got_request_exception.connect(self.handle_quart_exception)

            if self.capture_5xx or self.capture_4xx:
                quart.request_finished.connect(self.handle_request_end)

    async def handle_request_end(self, sender, response, **extra):
        code = response.status_code
        if code < 400:
            return
        elif 400 <= code < 500 and not self.capture_4xx:
            return
        elif code >= 500 and not self.capture_5xx:
            return

        lc = get_hybrid_context()
        lc.log_metadata({
            "msg": f"Quart `{code}` response",
            "status_code": code,
        })

    @staticmethod
    def exc_handler_patch(*args, original, **kwargs):
        get_hybrid_context().from_exception(sys.exception())
        return original(*args, **kwargs)

    @staticmethod
    async def handle_quart_exception(sender, exception: Exception, **extra):
        get_hybrid_context().from_exception(exception)

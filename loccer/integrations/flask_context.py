import flask

from ..bases import Integration


class FlaskContextIntegration(Integration):
    NAME = "flask"

    def gather(self) -> dict:
        data = {}
        if flask.request:
            data.update({
                "flask_context": True,
                "endpoint": (flask.request.endpoint or "<unknown>"),
                "client_ip": flask.request.remote_addr,
                "url": flask.request.path,
                "method": flask.request.method,
                "headers": dict(flask.request.headers),
                "user_agent": flask.request.headers.get("User-Agent", "<unknown>"),
            })
        else:
            data["flask_context"] = False
        return data

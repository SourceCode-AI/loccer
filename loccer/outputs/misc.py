from __future__ import annotations

import typing as t

from ..bases import OutputBase, LoccerOutput

if t.TYPE_CHECKING:
    from .. import Loccer
    from ..ltypes import JSONType


class InMemoryOutput(OutputBase):
    def __init__(self) -> None:
        self.logs: list[dict[str, JSONType]] = []

    def output(self, exc: LoccerOutput, lc: Loccer) -> None:
        json_data: dict[str, JSONType] = exc.as_json()
        json_data["session_id"] = lc.session.session_id

        self.logs.append(json_data)


class NullOutput(OutputBase):
    def output(self, exc: LoccerOutput, lc: Loccer) -> None:
        return None

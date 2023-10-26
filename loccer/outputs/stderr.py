from __future__ import annotations

import sys
import typing as t

from ..bases import OutputBase, LoccerOutput
from .file_stream import JSONStreamOutput

if t.TYPE_CHECKING:
    from .. import Loccer


class StderrOutput(OutputBase):
    def __init__(self) -> None:
        self.fd_out = JSONStreamOutput(fd=sys.stderr, compressed=False)

    def output(self, exc: LoccerOutput, lc: Loccer) -> None:
        self.fd_out.output(exc, lc=lc)

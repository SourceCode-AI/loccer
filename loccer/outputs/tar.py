from __future__ import annotations

import io
import os.path
import tarfile
import time
import typing as t

from ..bases import OutputBase, LoccerOutput, DEFAULT_MAX_LOGS, DEFAULT_MAX_LOG_SIZE
from ..formats import msgpack


if t.TYPE_CHECKING:
    from . import Loccer
    from ..tracing import Trace


class Tar(OutputBase):
    def __init__(
        self,
        filename: str,
        max_log_size: int = DEFAULT_MAX_LOG_SIZE,
        max_log_files: int = DEFAULT_MAX_LOGS,
    ) -> None:
        self.filename = filename
        self.max_log_size = max_log_size
        self.max_log_files = max_log_files

    def output(self, exc: LoccerOutput, lc: Loccer) -> None:
        raise RuntimeError("Not supported")

    def log_trace(self, trace: Trace) -> None:
        bin_trace = msgpack.pack(trace.snapshot())
        tinfo = tarfile.TarInfo(name=f"trace_{time.time()}.msgpack")
        tinfo.size = len(bin_trace)
        tinfo.type = tarfile.REGTYPE
        self.add_entry(tinfo, bin_trace)

    def add_entry(self, tarinfo: tarfile.TarInfo, data: bytes) -> None:
        mode = "a"
        if not os.path.exists(self.filename):
            mode = "w"

        with tarfile.open(self.filename, mode) as fd:
            fd.addfile(tarinfo, io.BytesIO(data))

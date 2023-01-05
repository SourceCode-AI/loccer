import sys

from ..bases import OutputBase, ExceptionData
from .file_stream import JSONStreamOutput


class StderrOutput(OutputBase):
    def __init__(self):
        self.fd_out = JSONStreamOutput(fd=sys.stderr, compressed=False)

    def output(self, exc: ExceptionData) -> None:
        self.fd_out.output(exc)

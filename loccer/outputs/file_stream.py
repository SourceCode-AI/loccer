import os
import json
import typing as t

from ..bases import OutputBase, ExceptionData


class JSONStreamOutput(OutputBase):
    def __init__(self, fd: t.TextIO, compressed=True):
        self.fd = fd
        self.compressed = compressed

        if self.compressed:
            self.dump_kwargs = {
                "separators": (",", ":")
            }
        else:
            self.dump_kwargs = {
                "indent": 2,
                "ensure_ascii": False
            }

    def output(self, exc: ExceptionData) -> None:
        data = json.dumps(exc.as_json(), **self.dump_kwargs)
        self.fd.write(data.strip() + os.linesep)


class JSONFileOutput(OutputBase):
    def __init__(self, filename, compressed=True):
        self.filename = filename
        self.compressed = compressed

    def output(self, exc: ExceptionData) -> None:
        with open(self.filename, "a") as fd:
            stream_out = JSONStreamOutput(fd=fd, compressed=self.compressed)
            stream_out.output(exc)

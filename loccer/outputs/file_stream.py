from __future__ import annotations

import os
import os.path
import shutil
import json
import gzip
import typing as t

from ..bases import OutputBase, LoccerOutput

if t.TYPE_CHECKING:
    from .. import Loccer
    from ..ltypes import JSONType


class LoccerJSONEncoder(json.JSONEncoder):
    def default(self, o: t.Any) -> t.Any:
        if o is None:
            return None
        if not isinstance(o, (int, str, list, bool, float, dict)):
            try:
                return repr(o)
            except Exception:
                return "CRITICAL ERROR: could not get repr of the object"

        return json.JSONEncoder.default(self, o)


class JSONStreamOutput(OutputBase):
    def __init__(self, fd: t.TextIO, compressed: bool = True) -> None:
        self.fd = fd
        self.compressed = compressed
        self.dump_kwargs: dict[str, t.Any]

        if self.compressed:
            self.dump_kwargs = {"separators": (",", ":")}  # pragma: no mutate
        else:
            self.dump_kwargs = {
                "indent": 2,  # pragma: no mutate
                "ensure_ascii": False,  # pragma: no mutate
            }

    def output(self, exc: LoccerOutput, lc: Loccer) -> None:
        json_data: dict[str, JSONType] = exc.as_json()
        json_data["session_id"] = lc.session.session_id
        data = json.dumps(json_data, cls=LoccerJSONEncoder, **self.dump_kwargs)
        self.fd.write(data.strip() + os.linesep)


class JSONFileOutput(OutputBase):
    def __init__(
        self,
        filename: str,
        compressed: bool = True,
        max_size: int = ((2**20) * 10),
        max_files: int = 10,
    ) -> None:
        """
        JSON output into file, one error report per line

        :param filename: Path to file
        :param compressed: Flag to turn on compressed json output stripping unnecessary whitespaces
        :param max_size: maximum error log size before the file is rotated, set to 0 to disable file rotation
        :param max_files: Maximum number of compressed error log backups to keep when rotating files
        """
        if max_size <= 10:
            raise ValueError("Max size must be greater than 10")

        if max_files < 0:
            raise ValueError("Max files must be 0 or greater number")

        self.filename = filename
        self.compressed = compressed
        self.max_size = max_size
        self.max_files = max_files

    def output(self, exc: LoccerOutput, lc: Loccer) -> None:
        with open(self.filename, "a") as fd:
            stream_out = JSONStreamOutput(fd=fd, compressed=self.compressed)
            stream_out.output(exc, lc=lc)

        if self.max_size:
            rotate(self.filename, self.max_size, self.max_files)


def rotate(filename: str, max_size: int, max_files: int = 10) -> bool:  # pragma: no mutate
    fstat = os.stat(filename)
    if fstat.st_size < max_size:
        return False

    for fnum in reversed(range(max_files - 1)):
        this_fname = f"{filename}.{fnum}.gz"
        new_fname = f"{filename}.{fnum+1}.gz"

        if os.path.exists(this_fname):
            shutil.copyfile(this_fname, new_fname)

        with open(filename, "r+b") as f_in:
            with gzip.open(f"{filename}.0.gz", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

            if f_in.seekable():
                f_in.seek(0)
            f_in.truncate()

    return True

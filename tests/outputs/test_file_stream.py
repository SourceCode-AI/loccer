import io
import json
import uuid
from unittest.mock import MagicMock

import pytest

from loccer.outputs import file_stream


obj = object()


class ReprFail:
    def __repr__(self):
        raise ValueError("One does not simply repr")


@pytest.mark.parametrize(
    "value, result",
    (
        (None, None),
        (True, True),
        ("string", "string"),
        (["a"], ["a"]),
        (4.2, 4.2),
        ({"a": "b"}, {"a": "b"}),
        (tuple(), []),
        (obj, repr(obj)),
        (ReprFail(), "CRITICAL ERROR: could not get repr of the object"),
    ),
)
def test_json_encoder(value, result):
    out = json.loads(json.dumps(value, cls=file_stream.LoccerJSONEncoder))
    assert out == result


def test_json_stream_output_settings(log_sample, lc):
    lc.session.captured = True
    fd = io.StringIO()
    stream_out = file_stream.JSONStreamOutput(fd)
    assert stream_out.compressed is True
    stream_out.output(log_sample, lc)
    output = fd.getvalue()
    assert output
    assert len(output.splitlines()) == 1
    decoded = json.loads(output)
    assert decoded
    assert decoded["session_id"] == lc.session.session_id

    fd = io.StringIO()
    stream_out = file_stream.JSONStreamOutput(fd, compressed=False)
    assert stream_out.compressed is False
    stream_out.output(log_sample, lc)
    output = fd.getvalue()
    assert output
    assert len(output.splitlines()) > 1
    decoded_2 = json.loads(output)
    assert decoded_2
    assert decoded == decoded_2


def test_json_file_output_settings():
    fname = str(uuid.uuid4())
    out = file_stream.JSONFileOutput(fname)
    assert out.filename == fname
    assert out.compressed is True
    assert out.max_size == ((2**20) * 10)
    assert out.max_files == 10

    file_stream.JSONFileOutput(fname, max_size=11)
    with pytest.raises(ValueError, match="^Max size must be greater than 10$"):
        file_stream.JSONFileOutput(fname, max_size=10)

    file_stream.JSONFileOutput(fname, max_files=0)
    with pytest.raises(ValueError, match="^Max files must be 0 or greater number$"):
        file_stream.JSONFileOutput(fname, max_files=-1)


def test_json_file_output(lc, log_sample, tmp_path):
    fname = tmp_path / str(uuid.uuid4())
    out = file_stream.JSONFileOutput(str(fname))
    out.output(log_sample, lc)

    logs = []
    for x in fname.read_text().splitlines():
        logs.append(json.loads(x))

    assert len(logs) == 1
    log = logs[0]
    assert log["data"] == log_sample.data
    assert log["session_id"] == lc.session.session_id

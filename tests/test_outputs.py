import gzip

import pytest

from loccer.outputs.file_stream import rotate, JSONFileOutput


def test_file_rotation(tmp_path):
    prefix = "blah"
    content = "TEST FILE CONTENT"
    max_size = 10
    assert len(prefix) < max_size
    assert len(prefix+content) > max_size

    fname = "test_file.log"
    fpath = tmp_path / fname
    first_bak = tmp_path / f"{fname}.0.gz"
    second_bak = tmp_path / f"{fname}.1.gz"
    fpath.write_text(prefix)

    assert fpath.exists()
    out = rotate(str(fpath), max_size, max_files=2)
    assert out is False
    assert fpath.exists()
    assert not first_bak.exists()

    fpath.write_text(prefix+content)
    out = rotate(str(fpath), max_size, max_files=2)
    assert out is True
    assert fpath.exists()
    assert fpath.read_text() == ""
    assert first_bak.exists()
    payload = gzip.decompress(first_bak.read_bytes()).decode()
    assert payload == prefix+content

    fpath.write_text(prefix + content)
    out = rotate(str(fpath), max_size, max_files=2)
    assert out is True
    assert fpath.exists()
    assert fpath.read_text() == ""
    assert first_bak.exists()
    payload = gzip.decompress(first_bak.read_bytes()).decode()
    assert payload == prefix + content
    assert second_bak.exists()
    payload = gzip.decompress(second_bak.read_bytes()).decode()
    assert payload == prefix + content

    fpath.write_text(prefix + content)
    out = rotate(str(fpath), max_size, max_files=2)
    assert out is True
    assert first_bak.exists()
    assert second_bak.exists()
    assert not (tmp_path/f"{fname}.2.gz").exists()


def test_invalid_json_file_output():
    with pytest.raises(ValueError):
        JSONFileOutput("ratata", max_size=-1)

    with pytest.raises(ValueError):
        JSONFileOutput("ratata", max_files=-1)

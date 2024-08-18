import os
import re
import tarfile
from unittest import mock
import uuid

import pytest

from loccer.outputs import tar


trace_regex = re.compile(r"^trace_\d+\.\d+\.msgpack$")


@pytest.fixture()
def chdir(tmp_path):
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        yield tmp_path
    finally:
        os.chdir(cwd)


def tar_entries(fname):
    with tarfile.open(fname, "r") as fd:
        return fd.getmembers()

def test_tar_log_trace(chdir):
    tname = f"{uuid.uuid4()}.tar"
    t = tar.Tar(tname)
    m = mock.MagicMock()
    m.snapshot = lambda : {}

    assert os.path.exists(tname) is False
    t.log_trace(m)
    assert os.path.exists(tname) is True
    entries = [x.name for x in tar_entries(tname)]
    assert len(entries) == 1
    assert trace_regex.match(entries[0])

    t.log_trace(m)
    entries = [x.name for x in tar_entries(tname)]
    assert len(entries) == 2
    assert trace_regex.match(entries[1])
    assert entries[0] != entries[1]

    os.unlink(tname)

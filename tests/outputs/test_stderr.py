import json

import loccer
from loccer.outputs.stderr import StderrOutput


def test_stderr_output(capsys):
    log_data = {"a": "b"}
    out = StderrOutput()
    assert out.fd_out.compressed is False

    lc = loccer.Loccer(output_handlers=(out,), integrations=())
    lc.session.captured = True
    lc.log_metadata(log_data)
    captured = capsys.readouterr()

    assert "\n" in captured.err
    str_out = captured.err.replace("\n", "")

    data = json.loads(str_out)
    assert data
    assert data["loccer_type"] == "metadata_log"
    assert data["data"] == log_data, data

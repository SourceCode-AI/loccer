import time

import pytest

import loccer
from loccer import tracing


def test_trace_creation():
    tr = tracing.Trace("test_trace")
    assert tracing.current_trace.get() is not tr

    ts1 = time.perf_counter_ns()
    ts2 = time.time()

    with tr:
        assert tr.start > ts1
        assert tr.start_ts >= ts2
        assert tr.end is None
        assert tr.label == "test_trace"
        assert tracing.current_trace.get() is tr
        assert tr.children == []
        assert tr.duration is None

        with tracing.Trace("trace2") as tr2:
            assert tracing.current_trace.get() is tr2
            assert tr.children == []
            assert tr.id != tr2.id

    assert tr.end > tr.start
    assert tr.duration > 0
    assert tracing.current_trace.get() is not tr


def test_span_creation():
    tr = tracing.Trace("test_trace")
    with tr:
        ts1 = time.perf_counter_ns()
        with tr.span("span1") as span1:
            assert isinstance(span1, tracing.Span)
            assert span1.trace is tr
            assert span1.parent is None
            assert span1.start > ts1
            assert span1.end is None
            assert span1.children == []

            with span1.span("span2") as span2:
                assert span2.parent is span1
                assert span2.start > span1.start
                assert span2.trace is tr
                assert len(span1.children) == 1
                assert span1.children[0] == span2

            assert span2.duration > 0
            assert span1.duration is None

        assert span1.duration > span2.duration


@pytest.mark.parametrize("obj", (
    tracing.Trace("tr1"),
    tracing.Trace("tr2").span("sp1")
))
def test_set_attributes(obj):
    attrs = {
        "k1": "v1",
        "k2": None,
        "k3": 3.14159
    }

    with obj:
        with obj.span("subspan") as subspan:
            assert obj.attributes is not subspan.attributes
            assert subspan.attributes == {}

        for k, v in attrs.items():
            obj.set(k, v)
            assert obj.attributes[k] == v

        assert subspan.attributes == {}

    assert obj.attributes == attrs
    assert obj.snapshot()["attributes"] == attrs




def test_make_span():
    assert tracing.current_trace.get() is None
    assert tracing.current_span.get() is None

    with tracing.Trace("tr1") as tr1:
        with tr1.span("sp1") as sp1:
            with tracing.make_span("test_span") as sp:
                assert sp.parent is sp1
                assert sp.trace is tr1
                assert tracing.current_span.get() is sp
                assert tracing.current_trace.get() is tr1

            assert tracing.current_span.get() is sp1

    assert tracing.current_trace.get() is None
    assert tracing.current_span.get() is None

    with tracing.Trace("tr1") as tr1:
        with tracing.make_span("test_span") as sp:
            assert sp.parent is None
            assert sp.trace is tr1
            assert tracing.current_span.get() is sp
            assert tracing.current_trace.get() is tr1

        assert tracing.current_span.get() is None

    assert tracing.current_trace.get() is None
    assert tracing.current_span.get() is None

    with tracing.make_span("test_span") as sp:
        assert tracing.current_trace.get() is None
        assert tracing.current_span.get() is sp
        assert tracing.current_span.get().trace is None

    assert tracing.current_trace.get() is None
    assert tracing.current_span.get() is None
    # TODO: test creating span without trace and then crating a trace to reassign span under the new trace
    pass


def test_trace_finished_cb():
    cb_value = None

    def _cb(trace: tracing.Trace) -> None:
        nonlocal cb_value
        cb_value = trace

    with tracing.Trace("tr1", finished_cb=_cb) as tr:
        assert cb_value is None

    assert cb_value is tr


def test_snapshot():
    with tracing.Trace("tr1") as tr1:
        with tr1.span("sp1") as sp1:
            for x in range(5):
                with sp1.span("sp2") as sp2:
                    sp1.set("iteration", x)
                    sp2.set("iteration", x)
                    tr1.snapshot()
                    sp1.snapshot()
                    sp2.snapshot()

    snapshot = tr1.snapshot()
    assert snapshot["label"] == tr1.label
    assert snapshot["attributes"] == {}
    assert snapshot["start_ts"] == tr1.start_ts
    assert snapshot["start"] == tr1.start
    assert snapshot["end"] == tr1.end
    assert len(snapshot["children"]) == 1

    sn1 = snapshot["children"][0]
    print(sn1)
    assert sn1["label"] == "sp1"
    assert sn1["start"] == sp1.start
    assert sn1["end"] == sp1.end
    assert len(sn1["children"]) == 5
    assert sn1["attributes"] == {"iteration": 4}

    for x in range(5):
        subsn = sn1["children"][x]
        assert subsn["label"] == "sp2"
        assert subsn["attributes"] == {"iteration": x}


def test_recursive_span_decorator():
    @loccer.span("rec")
    def _rec(value):
        loccer.span.set("value", value)
        if value > 1:
            return _rec(value-1)

    with loccer.trace("tr1") as tr:
        _rec(2)

    assert len(tr.children) == 1
    sp1 = tr.children[0]
    assert sp1.attributes["value"] == 2
    assert len(sp1.children) == 1
    sp2 = sp1.children[0]
    assert sp2.attributes["value"] == 1
    assert sp2.children == []


def test_tracing_ctx_id1():
    val = None

    for x in range(5):
        # inlined span
        with loccer.trace("tr") as tr:
            ctx_id = tr.ctx_id
            assert ctx_id is not None
            assert ctx_id != 0

            if val is None:
                val = ctx_id
            assert ctx_id == val

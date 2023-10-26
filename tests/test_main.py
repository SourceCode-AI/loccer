import sys
import uuid
from unittest.mock import patch, MagicMock

import loccer
from loccer.bases import Integration


def test_capture_exception_call(in_memory):
    assert in_memory.logs == []

    try:
        raise AssertionError("test_capture_exception_call")
    except AssertionError:
        loccer.capture_exception()

    assert len(in_memory.logs) == 2
    assert in_memory.logs[0]["loccer_type"] == "session"
    log = in_memory.logs[1]
    assert log["loccer_type"] == "exception"
    assert log["exc_type"] == "AssertionError"
    assert log["msg"] == "test_capture_exception_call"


def test_capture_exception_context_manager(in_memory):
    assert in_memory.logs == []

    with loccer.capture_exception:
        raise AssertionError("test_capture_exception_context_manager")

    assert len(in_memory.logs) == 2
    assert in_memory.logs[1]["exc_type"] == "AssertionError"
    assert in_memory.logs[1]["msg"] == "test_capture_exception_context_manager"


def test_repr_error(in_memory):
    class A:
        def __repr__(self):
            self.err()

        def err(self):
            raise RuntimeError("err", "what?")

    with loccer.capture_exception:
        obj = A()
        obj.err()

    assert len(in_memory.logs) == 2
    log = in_memory.logs[1]

    obj_repr = log["frames"][0]["locals"]["obj"]
    assert obj_repr == "Error getting repr of the object: `RuntimeError: err; what?`"


def test_capture_exception_decorator(in_memory):
    assert in_memory.logs == []

    @loccer.capture_exception
    def func():
        """function docstring"""
        raise AssertionError("test_capture_exception_decorator")

    assert func.__doc__ == "function docstring"

    func()

    assert len(in_memory.logs) == 2
    assert in_memory.logs[1]["exc_type"] == "AssertionError"
    assert in_memory.logs[1]["msg"] == "test_capture_exception_decorator"


def test_basic_integration(integration, in_memory):
    val = str(uuid.uuid4())

    with patch.dict(integration.data) as m:
        integration.data["test_basic_integration"] = val

        with loccer.capture_exception:
            raise AssertionError("test_basic_integration")

    assert len(in_memory.logs) == 2
    log = in_memory.logs[1]
    assert log["exc_type"] == "AssertionError"
    assert log["msg"] == "test_basic_integration"

    assert integration.NAME in log["integrations"]
    assert log["integrations"][integration.NAME]["test_basic_integration"] == val, log["integrations"]


def test_log_metadata(in_memory):
    log_data = {"a": "b"}

    assert in_memory.logs == []
    loccer.capture_exception.log_metadata(log_data)
    assert len(in_memory.logs) == 2
    sess = in_memory.logs[0]
    assert sess["loccer_type"] == "session"
    log = in_memory.logs[1]
    assert log["loccer_type"] == "metadata_log"
    assert log["session_id"] == sess["session_id"]
    assert sess["session_id"] is not None
    assert log["data"] == log_data
    assert isinstance(log["integrations"], dict)


def test_session_information(in_memory):
    assert in_memory.logs == []
    assert loccer.capture_exception.session.captured is False

    try:
        raise AssertionError("test_capture_exception_call")
    except AssertionError:
        loccer.capture_exception()

    assert len(in_memory.logs) == 2
    sess = in_memory.logs[0]
    assert sess["loccer_type"] == "session"
    session_id = sess["session_id"]
    assert isinstance(session_id, str)
    assert session_id == loccer.capture_exception.session.session_id
    assert sess["session_id"] == session_id
    assert set(sess.keys()) == {"loccer_type", "session_id", "data"}

    log = in_memory.logs[1]
    assert log["loccer_type"] == "exception"
    assert log["session_id"] == session_id

    in_memory.logs.clear()
    assert loccer.capture_exception.session.captured is True
    assert len(in_memory.logs) == 0
    loccer.capture_exception.log_metadata("Test data")
    # No session data will be generated because it is marked as already captured
    assert len(in_memory.logs) == 1
    log = in_memory.logs[0]
    assert log["loccer_type"] == "metadata_log"


def test_defaults_loccer():
    assert isinstance(loccer.capture_exception, loccer.Loccer)
    lc = loccer.Loccer()

    assert len(lc.output_handlers) == 1
    assert isinstance(lc.output_handlers[0], loccer.StderrOutput)
    assert len(lc.integrations) == 2
    assert isinstance(lc.integrations[0], loccer.PlatformIntegration)
    assert isinstance(lc.integrations[1], loccer.PackagesIntegration)
    assert lc.suppress_exception is False
    assert lc.exc_hook is loccer.excepthook


def test_defaults_hybrid_context():
    hc = loccer.HybridContext()
    assert hc.exc_handler is sys.excepthook

    with patch("sys.exc_info") as exc_info, patch("sys.excepthook") as m:
        exc_info.return_value = (None,)*3
        hc._call()
        m.assert_not_called()
        exc_info.return_value = (42,)*3
        hc._call()
        m.assert_called_once_with(42, 42, 42)

        m.reset_mock()
        exc_info.return_value = (42, None, None)
        hc._call()
        m.assert_not_called()
        exc_info.return_value = (None, 42, None)
        hc._call()
        m.assert_not_called()

def test_defaults_install():
    called = None
    previous = lambda: None
    sys.excepthook = previous
    test_data = (1, 2, 3)

    def _exc_hook(etype, etval, etb, lc, previous_hook) -> None:
        nonlocal called
        assert isinstance(lc, loccer.Loccer)
        assert previous_hook is previous
        called = (etype, etval, etb)

    with patch.object(loccer, "excepthook", new=_exc_hook) as m:
        lc = loccer.install()

    assert loccer.capture_exception is lc
    assert sys.excepthook != sys.__excepthook__

    sys.excepthook(*test_data)
    assert called == test_data

    called = None
    lc.exc_hook(*test_data)
    assert called == test_data

    lc2 = loccer.install()
    called = None
    try:
        1 /0
    except ArithmeticError as exc:
        sys.excepthook(type(exc), exc, exc.__traceback__)
        assert called == (type(exc), exc, exc.__traceback__)

    loccer.restore()
    assert loccer.capture_exception is not lc
    assert isinstance(loccer.capture_exception, loccer.HybridContext)
    assert sys.excepthook == sys.__excepthook__


def test_install():
    with patch("loccer.excepthook") as m:
        lc = loccer.install(preserve_previous=False)
        lc.exc_hook()
        m.assert_called_once_with(lc=lc, previous_hook=None)


def test_failing_integration(in_memory):
    class FailIntegration(Integration):
        NAME = "fail_integration"

        def gather(self, context):
            raise RuntimeError("gather error")

        def session_data(self):
            raise RuntimeError("session error")

    loccer.capture_exception.integrations = (FailIntegration(),)
    loccer.capture_exception.log_metadata("Test data")
    pattern = "CRITICAL: error while calling the integration to gather data:\nTraceback (most recent call last):\n"

    assert len(in_memory.logs) == 2
    sess = in_memory.logs[0]
    fail_msg = sess["data"]["fail_integration"]
    assert fail_msg.startswith(pattern), fail_msg
    log = in_memory.logs[1]
    fail_msg = log["integrations"]["fail_integration"]
    assert fail_msg.startswith(pattern), fail_msg

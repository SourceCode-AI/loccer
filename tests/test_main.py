import loccer


def test_capture_exception_call(in_memory):
    assert in_memory.logs == []

    try:
        raise AssertionError("test_capture_exception_call")
    except AssertionError:
        loccer.capture_exception()

    assert len(in_memory.logs) == 1
    assert in_memory.logs[0]["exc_type"] == "AssertionError"
    assert in_memory.logs[0]["msg"] == "test_capture_exception_call"


def test_capture_exception_context_manager(in_memory):
    assert in_memory.logs == []

    with loccer.capture_exception:
        raise AssertionError("test_capture_exception_context_manager")


    assert len(in_memory.logs) == 1
    assert in_memory.logs[0]["exc_type"] == "AssertionError"
    assert in_memory.logs[0]["msg"] == "test_capture_exception_context_manager"


def test_capture_exception_decorator(in_memory):
    assert in_memory.logs == []

    @loccer.capture_exception
    def func():
        raise AssertionError("test_capture_exception_decorator")

    func()

    assert len(in_memory.logs) == 1
    assert in_memory.logs[0]["exc_type"] == "AssertionError"
    assert in_memory.logs[0]["msg"] == "test_capture_exception_decorator"

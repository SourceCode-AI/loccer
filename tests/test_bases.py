from loccer import bases

global_value = "test global value"


def test_exception_data():
    local_value = "test local value"

    try:
        1 / 0
    except ArithmeticError as exc:
        edata = bases.ExceptionData.from_exception(exc)
        # edata.traceback = exc.__traceback__
        json_data = edata.as_json()

    print(json_data)
    assert "globals" in json_data
    assert json_data["globals"]["global_value"] == repr(global_value)
    assert "__builtins__" not in json_data["globals"]
    frame = json_data["frames"][0]
    assert frame["filename"].endswith("test_bases.py")
    assert frame["lineno"] > 0
    assert frame["name"] == "test_exception_data"
    assert frame["line"] == "1 / 0"
    # FIXME assert frame["locals"]["local_value"] == repr(local_value)
    assert json_data["timestamp"]
    assert json_data["exc_type"] == "ZeroDivisionError"
    assert json_data["msg"] == "division by zero"

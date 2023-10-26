import pytest

from loccer import utils


obj = object()


@pytest.mark.parametrize("in_obj,expected", ((None, None), (obj, repr(obj))))
def test_quickformat(in_obj, expected):
    output = utils.quick_format(in_obj)
    assert output == expected

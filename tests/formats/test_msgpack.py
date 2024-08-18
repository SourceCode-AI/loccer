from loccer.formats import msgpack

import pytest
import binascii


@pytest.mark.parametrize(
    "data, output",
    (
        (None, b"\xc0"),
        (True, b"\xc3"),
        (False, b"\xc2"),
        (0, "00"),
        (42, "2A"),
        (0.0, b"\xcb\x00\x00\x00\x00\x00\x00\x00\x00"),
        (3.1415, b"\xcb@\t!\xca\xc0\x83\x12o"),
        ("", "A0"),
        ("hello", "A568656C6C6F"),
        (b"", b"\xc4\x00"),
        (b"hello", "C40568656C6C6F"),
        ([1, None, "hi"], "9301C0A26869"),
        ({"k": "v", "k2": None}, "82A16BA176A26B32C0")
    )
)
def test_pack(data, output: bytes):
    if isinstance(output, str):
        output = binascii.unhexlify(output)

    out = msgpack.pack(data)
    hex = binascii.hexlify(out, sep=" ", bytes_per_sep=1).upper()
    assert out == output, hex


@pytest.mark.parametrize("value", (
    object(),
    pytest,
))
def test_pack_invalid(value):
    with pytest.raises(ValueError, match=r"^Unknown data type: `.+`: `.+`$"):
        msgpack.pack(value)

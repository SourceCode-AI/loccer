"""
Subset of msgpack format for data serialization

Specification taken from: https://github.com/msgpack/msgpack/blob/master/spec.md
"""

from __future__ import annotations

import struct
import uuid
import typing as t


T_pack = bytes


def pack_none() -> T_pack:
    return b"\xc0"

def pack_bool(value: bool) -> T_pack:
    if value:
        return b"\xc3"
    else:
        return b"\xc2"

def pack_int(value: int) -> T_pack:
    bits = value.bit_length()

    if value >= 0:
        if bits <= 7:
            return struct.pack(">B", value)
        elif bits <= 8:
            return b"\xcc" + struct.pack(">B", value)
        elif bits <= 16:
            return b"\xcd" + struct.pack(">H", value)
        elif bits <= 32:
            return b"\xce" + struct.pack(">I", value)
        else:
            return b"\xcf" + struct.pack(">Q", value)
    else:
        if bits <= 5:
            return struct.pack(">b", ((0b111<<5)|value))
        elif bits <= 8:
            return b"\xd0" + struct.pack(">b", value)
        elif bits <= 16:
            return b"\xd1" + struct.pack(">h", value)
        elif bits <= 32:
            return b"\xd2" + struct.pack(">i", value)
        else:
            return b"\xd3" + struct.pack(">q", value)


def pack_float(value: float) -> T_pack:
    # TODO: optimize for different sizes
    return b"\xcb" + struct.pack(">d", value)


def pack_str(value: str) -> T_pack:
    v_bytes: bytes = value.encode("utf-8")
    v_len = len(v_bytes)
    p = b""

    if v_len <= 31:
        p += struct.pack(">B", ((0b101<<5) | v_len))
    elif v_len <= ((2**8)-1):
        p += b"\xd9"
        p += struct.pack(">B", v_len)
    elif v_len <= ((2**16)-1):
        p += b"\xda"
        p += struct.pack(">H", v_len)
    else:
        p += b"\xdb"
        p += struct.pack(">L", v_len)

    return p + v_bytes

def pack_bytes(value: bytes) -> T_pack:
    v_len = len(value)

    if v_len <= ((2**8)-1):
        return b"\xc4" + struct.pack(">B", v_len) + value
    elif v_len <= ((2**16)-1):
        return b"\xc5" + struct.pack(">H", v_len) + value
    else:
        return b"\xc6" + struct.pack(">L", len(value)) + value


def pack_list(values: list) -> T_pack:
    v_len = len(values)
    p = b""

    if v_len <= 15:
        p += struct.pack(">B", ((0b1001<<4)|v_len))
    elif v_len <= ((2**16)-1):
        p += b"\xdc" + struct.pack(">H", v_len)
    else:
        p += b"\xdd" + struct.pack(">L", len(values))

    for x in values:
        p+= pack(x)

    return p


def pack_dict(values: dict) -> T_pack:
    v_len = len(values)
    p = b""

    if v_len <= 15:
        p += struct.pack(">B", ((0b1000<<4)|v_len))
    elif v_len <= ((2**16)-1):
        p += b"\xde" + struct.pack(">H", v_len)
    else:
        p += b"\xdf" + struct.pack(">L", len(values))

    for k, v in values.items():
        p+= pack(k)+pack(v)

    return p


def pack(value) -> T_pack:
    if value is None:
        return pack_none()
    elif isinstance(value, bool):
        return pack_bool(value)
    elif isinstance(value, int):
        return pack_int(value)
    elif isinstance(value, float):
        return pack_float(value)
    elif isinstance(value, str):
        return pack_str(value)
    elif isinstance(value, bytes):
        return pack_bytes(value)
    elif isinstance(value, list):
        return pack_list(value)
    elif isinstance(value, dict):
        return pack_dict(value)
    elif isinstance(value, uuid.UUID):
        return pack_str(value.hex)

    raise ValueError(f"Unknown data type: `{type(value)}`: `{value}`")

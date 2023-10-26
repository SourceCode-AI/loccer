from contextvars import ContextVar
import typing as t

from .ltypes import JSONType


def quick_format(obj: t.Any) -> JSONType:
    if obj is None:
        return obj
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, ContextVar):
        return obj.name
    else:
        return repr(obj)

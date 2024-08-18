from contextvars import ContextVar
import typing as t

from .ltypes import JSONType


def quick_format(obj: t.Any, allow_dict: bool = False) -> JSONType:
    if obj is None:
        return obj
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, ContextVar):
        return obj.name
    elif allow_dict and isinstance(obj, dict):
        return {
            k: quick_format(v) for (k, v) in obj.items()
        }
    else:
        return repr(obj)

import typing as t
from types import TracebackType


JSONType: t.TypeAlias = dict[str, "JSONType"] | list["JSONType"] | str | int | float | bool | None
T_exc_type: t.TypeAlias = t.Type[BaseException]
T_exc_val: t.TypeAlias = BaseException
T_exc_tb: t.TypeAlias = t.Optional[TracebackType]
T_exc_hook: t.TypeAlias = t.Callable[[T_exc_type, T_exc_val, T_exc_tb], t.Any]

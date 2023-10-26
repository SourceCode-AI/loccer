import typing as t
from types import TracebackType


T = t.TypeVar("T")  # pragma: no mutate
U = t.TypeVar("U")  # pragma: no mutate
V = t.TypeVar("V")  # pragma: no mutate
JSONType = t.Union[dict[str, "JSONType"], list["JSONType"], str, int, float, bool, None]  # pragma: no mutate
T_exc_type = t.Type[BaseException]  # pragma: no mutate
T_exc_val = BaseException  # pragma: no mutate
T_exc_tb = t.Optional[TracebackType]  # pragma: no mutate
T_exc_hook = t.Callable[[T_exc_type, T_exc_val, T_exc_tb], t.Any]  # pragma: no mutate

import asyncio
from contextvars import Context, ContextVar, copy_context
import socket
import sys
import typing as t

from .. import get_hybrid_context
from ..bases import Integration, LoccerOutput
from ..ltypes import JSONType
from ..utils import quick_format


class LoopExceptionContext(t.TypedDict, total=False):  # pragma: no mutate
    message: str
    exception: Exception
    future: asyncio.Future
    task: asyncio.Task
    handle: asyncio.Handle
    protocol: asyncio.Protocol
    transport: asyncio.Transport
    socket: socket.socket
    asyncgen: t.AsyncGenerator


class AsyncioContextIntegration(Integration):
    """
    Integration with the asyncio context
    """

    NAME = "asyncio"

    _loop_ctx: ContextVar[t.Optional[LoopExceptionContext]] = ContextVar("loop_ctx", default=None)

    def __init__(self, dump_coros: bool = True, dump_context: bool = True):
        self._dump_coros = dump_coros
        self._dump_ctx = dump_context

    def gather(self, context: LoccerOutput) -> JSONType:
        data: dict[str, JSONType] = {}

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None

        if self._dump_coros:
            data["coros"] = self.dump_coros(loop)

        if self._dump_ctx:
            try:
                ctx: t.Optional[LoopExceptionContext] = self._loop_ctx.get()
                if ctx is not None:
                    data["loop_context"] = self.dump_contextvars(ctx)

                global_ctx = copy_context()
                data["global_context"] = self.dump_contextvars(global_ctx)
            except LookupError:
                pass

        return data

    def session_data(self) -> JSONType:
        return None

    def loop_exception_handler(self, loop: asyncio.AbstractEventLoop, context: LoopExceptionContext) -> None:
        ctx = copy_context()
        ctx.run(self._loop_exception_handler, loop, context)

    def _loop_exception_handler(self, loop: asyncio.AbstractEventLoop, context: LoopExceptionContext) -> None:
        self._loop_ctx.set(context)
        lc = get_hybrid_context()
        exc: t.Optional[BaseException]

        if "exception" in context:
            exc = context.get("exception")
        else:
            _, exc, _ = sys.exc_info()

        if exc is not None:
            lc.from_exception(exc)
        else:
            lc.log_metadata({"msg": "Unknown exception in the asyncio loop"})

    @staticmethod
    def dump_contextvars(ctx: t.Union[Context, LoopExceptionContext]) -> JSONType:
        return {str(quick_format(name)): repr(value) for (name, value) in ctx.items()}

    @staticmethod
    def dump_coros(loop: t.Optional[asyncio.AbstractEventLoop] = None) -> JSONType:
        data: dict[str, JSONType] = {}

        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return None

        for task in asyncio.all_tasks(loop):
            name = task.get_name()
            data[name] = {"coro": repr(task.get_coro()), "is_done": task.done()}

        return data

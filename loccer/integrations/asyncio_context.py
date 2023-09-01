import asyncio
import contextvars
import sys

from .. import get_hybrid_context
from ..bases import Integration, LoccerOutput, JSONType


class AsyncioContextIntegration(Integration):
    """
    Integration with the asyncio context
    """
    NAME = "asyncio"

    _loop_ctx = contextvars.ContextVar("loop_ctx", default=None)

    def __init__(
            self,
            dump_coros: bool = True,
            dump_context: bool = True
    ):
        self._dump_coros = dump_coros
        self._dump_ctx = dump_context

    def gather(self, context: LoccerOutput) -> JSONType:
        data: JSONType = {}

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return data

        if self._dump_coros:
            data["coros"] = self.dump_coros(loop)

        if self._dump_ctx:
            try:
                ctx = self._loop_ctx.get()
                data["loop_context"] = self.dump_contextvars(ctx)
            except LookupError:
                pass

        return data

    def loop_exception_handler(self, loop: asyncio.AbstractEventLoop, context: contextvars.Context) -> None:
        ctx = contextvars.copy_context()
        ctx.run(self._loop_exception_handler, loop, context)

    def _loop_exception_handler(self, loop: asyncio.AbstractEventLoop, context: contextvars.Context) -> None:
        self._loop_ctx.set(context)
        lc = get_hybrid_context()

        if "exception" in context:
            exc = context.get("exception")
        else:
            exc = sys.exception()

        if exc is not None:
            lc.from_exception(exc)
        else:
            lc.log_metadata({
                "msg": "Unknown exception in the asyncio loop"
            })

    @staticmethod
    def dump_contextvars(ctx: contextvars.Context) -> JSONType:
        return {
            name: repr(value) for (name, value) in ctx.items()
        }

    @staticmethod
    def dump_coros(loop: asyncio.AbstractEventLoop|None=None) -> JSONType:
        data = {}

        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return data

        for task in asyncio.all_tasks(loop):
            name = task.get_name()
            data[name] = {
                "coro": repr(task.get_coro()),
                "is_done": task.done()
            }

        return data

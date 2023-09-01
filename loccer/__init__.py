from __future__ import annotations

import os
import sys
import traceback as tb_module
import typing as t
from functools import partial, wraps
from unittest.mock import patch

from . import bases
from .outputs.misc import NullOutput
from .outputs.stderr import StderrOutput
from .integrations.platform_context import PlatformIntegration
from .ltypes import T_exc_val, T_exc_type, T_exc_tb, T_exc_hook, JSONType


DEFAULT_OUTPUT = (
    StderrOutput(),
)
DEFAULT_INTEGRATIONS = (
    PlatformIntegration(),
)


class HybridContext:
    def __init__(self, suppress_exception: bool=False):
        self.suppress_exception = suppress_exception

    def __call__(self, func=None):
        if callable(func):
            return self._decorator(func)
        else:
            self._call()

    def __enter__(self) -> HybridContext:
        return self

    def __exit__(self, exc_type: T_exc_type, exc_val: T_exc_val, exc_tb: T_exc_tb) -> bool:
        self.exc_handler(exc_type, exc_val, exc_tb)
        return self.suppress_exception

    @property
    def exc_handler(self) -> t.Optional[T_exc_hook]:
        return sys.excepthook

    def log_metadata(self, data: JSONType):
        pass

    def from_exception(self, exc: BaseException) -> None:
        self.exc_handler(type(exc), exc, exc.__traceback__)

    def _decorator(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return wrapper

    def _call(self):
        exc_type, exc_val, exc_tb = sys.exc_info()
        self.exc_handler(exc_type, exc_val, exc_tb)


class Loccer(HybridContext):
    def __init__(
        self,
        output_handlers: t.Sequence[bases.OutputBase] = DEFAULT_OUTPUT,
        integrations: t.Sequence[bases.Integration] = DEFAULT_INTEGRATIONS,
        exc_hook=None, **kwargs
    ):
        super().__init__(**kwargs)

        if exc_hook is None:
            exc_hook = excepthook

        self.exc_hook = exc_hook
        self.output_handlers = output_handlers
        self.integrations = integrations
        for x in integrations:
            x.activate(self)

    @property
    def exc_handler(self) -> T_exc_hook:
        kwargs = {}
        if self.integrations:
            kwargs["integrations"] = self.integrations

        if self.output_handlers:
            kwargs["output_handlers"] = self.output_handlers

        if kwargs:
            return partial(self.exc_hook, **kwargs)
        else:
            return self.exc_hook

    def log_metadata(self, data: JSONType):
        log = bases.MetadataLog(data)

        for x in self.integrations:
            log.integrations_data[x.NAME] = x.gather(log)

        for out_handler in self.output_handlers:
            out_handler.output(log)


capture_exception = HybridContext()


def excepthook(
        type: bases.T_exc_type,
        value: bases.T_exc_val,
        traceback: bases.T_exc_tb,
        output_handlers:  t.Sequence[bases.OutputBase] = (),
        integrations: t.Sequence[bases.Integration] = (),
        previous_hook: t.Optional[T_exc_hook]=None
    ):

    with patch("traceback.repr", new=_repr_mock):
        exc_data = bases.ExceptionData.from_exception(value, capture_locals=True)

    exc_data.traceback = traceback

    for x in integrations:
        try:
            exc_data.integrations_data[x.NAME] = x.gather(exc_data)
        except Exception as exc:
            desc = ["CRITICAL: error while calling the integration to gather data: "] + list(tb_module.format_exception(exc))
            exc_data.integrations_data[x.NAME] = os.linesep.join(desc)

    if output_handlers:
        for out_handler in output_handlers:
            out_handler.output(exc_data)

    if previous_hook:
        previous_hook(type, value, traceback)


def _repr_mock(obj: t.Any) -> str:
    try:
        return repr(obj)
    except Exception as exc:
        exc_desc = str(exc.__class__.__name__)
        if exc.args:
            exc_desc = f"{exc_desc}: {'; '.join(exc.args)}"

        return f"Error getting repr of the object: `{exc_desc}`"


def get_hybrid_context() -> HybridContext:
    return capture_exception


def install(
    *,
    preserve_previous=True,
    output_handlers:  t.Sequence[bases.OutputBase] = DEFAULT_OUTPUT,
    integrations: t.Sequence[bases.Integration] = DEFAULT_INTEGRATIONS
    ) -> Loccer:
    """
    Installs loccer as a global exception handler and activates all it's integrations

    :param preserve_previous: Forward all exceptions to the previous/original value of sys.excepthook as well
    :param output_handlers: List of output handlers for storing captured exceptions
    :param integrations: List of loccer integrations
    :return: Instance of loccer that has been installed as the global exception hook
    """
    global capture_exception
    previous = sys.excepthook
    kwargs = {
        "output_handlers": output_handlers,
        "integrations": integrations
    }
    if preserve_previous:
        kwargs["previous_hook"] = previous

    exc_hook = partial(excepthook, **kwargs)
    sys.excepthook = exc_hook
    lc = Loccer(
        output_handlers=output_handlers,
        integrations=integrations,
        exc_hook=exc_hook
    )
    capture_exception = lc
    return lc


def restore() -> None:
    """
    Restore exception handling to the previous state
    Can be used to "uninstall" loccer at runtime
    """
    global capture_exception

    capture_exception = HybridContext()
    sys.excepthook = sys.__excepthook__

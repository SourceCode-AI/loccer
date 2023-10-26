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
from .integrations.packages_context import PackagesIntegration
from .ltypes import T_exc_val, T_exc_type, T_exc_tb, T_exc_hook, JSONType, T, U, V


DEFAULT_OUTPUT = (StderrOutput(),)
DEFAULT_INTEGRATIONS = (
    PlatformIntegration(),
    PackagesIntegration(),
)


class HybridContext:
    def __init__(self, suppress_exception: bool = False):
        self.suppress_exception: bool = suppress_exception

    def __call__(self, func: t.Optional[t.Callable[..., U]] = None) -> t.Optional[t.Callable[..., t.Optional[U]]]:
        if callable(func):
            return self._decorator(func)
        else:
            self._call()
            return None

    def __enter__(self) -> HybridContext:
        return self

    def __exit__(self, exc_type: T_exc_type, exc_val: T_exc_val, exc_tb: T_exc_tb) -> bool:
        self.exc_handler(exc_type, exc_val, exc_tb)
        return self.suppress_exception

    @property
    def exc_handler(self) -> T_exc_hook:
        return sys.excepthook

    def emit_output(self, output: bases.LoccerOutput) -> None:
        return None

    def log_metadata(self, data: JSONType) -> None:
        pass

    def from_exception(self, exc: t.Optional[BaseException]) -> None:
        if exc is not None:
            self.exc_handler(type(exc), exc, exc.__traceback__)

    def _decorator(self, func: t.Callable[..., U]) -> t.Callable[..., t.Optional[U]]:
        @wraps(func)
        def wrapper(*args: T, **kwargs: V) -> t.Optional[U]:
            with self:
                return func(*args, **kwargs)

            return None

        return wrapper

    def _call(self) -> None:
        exc_type, exc_val, exc_tb = sys.exc_info()
        if exc_type and exc_val:
            self.exc_handler(exc_type, exc_val, exc_tb)


T_loccer_exchook = t.Callable[
    [T_exc_type, T_exc_val, T_exc_tb, t.Optional[HybridContext], t.Optional[T_exc_hook]], None  # pragma: no mutate
]  # pragma: no mutate


class Loccer(HybridContext):
    def __init__(
        self,
        output_handlers: t.Sequence[bases.OutputBase] = DEFAULT_OUTPUT,
        integrations: t.Sequence[bases.Integration] = DEFAULT_INTEGRATIONS,
        exc_hook: t.Optional[T_loccer_exchook] = None,
        **kwargs: t.Any,
    ):
        super().__init__(**kwargs)
        self.exc_hook: T_loccer_exchook

        if exc_hook is None:
            self.exc_hook = excepthook
        else:
            self.exc_hook = exc_hook

        self.output_handlers = output_handlers
        self.integrations = integrations
        self.session = bases.Session(self)

        for x in integrations:
            x.activate(self)

    @property
    def exc_handler(self) -> T_exc_hook:
        return partial(self.exc_hook, lc=self)

    def emit_output(self, output: bases.LoccerOutput) -> None:
        for x in self.integrations:
            try:
                integration_data = x.gather(output)
                if integration_data is not None:
                    output.integrations_data[x.NAME] = integration_data
            except Exception as exc:
                desc = ["CRITICAL: error while calling the integration to gather data:"] + list(
                    tb_module.format_exception(type(exc), exc, exc.__traceback__)
                )
                output.integrations_data[x.NAME] = os.linesep.join(desc)

        if self.output_handlers:
            sess = self.session.captured
            if not sess:
                self.session.captured = True

            for out_handler in self.output_handlers:
                if not sess:
                    out_handler.output(self.session, lc=self)

                out_handler.output(output, lc=self)

    def log_metadata(self, data: JSONType) -> None:
        log = bases.MetadataLog(data)
        self.emit_output(log)


capture_exception = HybridContext()  # pragma: no mutate


def excepthook(
    type: T_exc_type,
    value: T_exc_val,
    traceback: T_exc_tb,
    lc: t.Optional[HybridContext],
    previous_hook: t.Optional[T_exc_hook] = None,
) -> None:
    with patch("traceback.repr", new=_repr_mock):
        exc_data = bases.ExceptionData.from_exception(value, capture_locals=True)

    if lc is not None:
        lc.emit_output(exc_data)

    if previous_hook is not None:
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
    preserve_previous: bool = True,
    output_handlers: t.Sequence[bases.OutputBase] = DEFAULT_OUTPUT,
    integrations: t.Sequence[bases.Integration] = DEFAULT_INTEGRATIONS,
) -> Loccer:
    """
    Installs loccer as a global exception handler and activates all it's integrations

    :param preserve_previous: Forward all exceptions to the previous/original value of sys.excepthook as well
    :param output_handlers: List of output handlers for storing captured exceptions
    :param integrations: List of loccer integrations
    :return: Instance of loccer that has been installed as the global exception hook
    """
    global capture_exception

    lc = Loccer(output_handlers=output_handlers, integrations=integrations)
    previous_hook: t.Optional[T_exc_hook]

    if preserve_previous:
        previous_hook = sys.excepthook
    else:
        previous_hook = None

    exc_hook = partial(excepthook, lc=lc, previous_hook=previous_hook)
    sys.excepthook = exc_hook
    lc.exc_hook = exc_hook
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

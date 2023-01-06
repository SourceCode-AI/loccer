from __future__ import annotations

import sys
import typing as t
from functools import partial, wraps

import loccer
from . import bases
from .outputs.misc import NullOuput
from .outputs.stderr import StderrOutput
from .integrations.platform_context import PlatformIntegration


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

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.exc_handler(exc_type, exc_val, exc_tb)
        return self.suppress_exception

    @property
    def exc_handler(self):
        return sys.excepthook

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

    @property
    def exc_handler(self):
        kwargs = {}
        if self.integrations:
            kwargs["integrations"] = self.integrations

        if self.output_handlers:
            kwargs["output_handlers"] = self.output_handlers

        if kwargs:
            return partial(self.exc_hook, **kwargs)
        else:
            return self.exc_hook


capture_exception = HybridContext()


def excepthook(
        type,
        value,
        traceback,
        output_handlers:  t.Sequence[bases.OutputBase] = (),
        integrations: t.Sequence[bases.Integration] = (),
        previous_hook=None
    ):
    exc_data = bases.ExceptionData.from_exception(value, capture_locals=True)
    exc_data.traceback = traceback

    for x in integrations:
        exc_data.integrations_data[x.NAME] = x.gather()

    if output_handlers:
        for out_handler in output_handlers:
            out_handler.output(exc_data)

    if previous_hook:
        previous_hook(type, value, traceback)


def install(
    *,
    preserve_previous=True,
    output_handlers:  t.Sequence[bases.OutputBase] = DEFAULT_OUTPUT,
    integrations: t.Sequence[bases.Integration] = DEFAULT_INTEGRATIONS
    ) -> Loccer:
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
    lc = loccer.Loccer(
        output_handlers=output_handlers,
        integrations=integrations,
        exc_hook=exc_hook
    )
    capture_exception = lc
    return lc

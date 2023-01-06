from __future__ import annotations

import sys
import typing as t
from functools import partial, wraps

from . import bases
from .outputs.misc import NullOuput
from .outputs.stderr import StderrOutput


DEFAULT_OUTPUT = StderrOutput()


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
    def __init__(self, handlers: t.Sequence[bases.OutputBase] = (), exc_hook=None, **kwargs):
        super().__init__(**kwargs)

        if exc_hook is None:
            exc_hook = excepthook

        self.exc_hook = exc_hook
        self.handlers = handlers

    @property
    def exc_handler(self):
        return partial(self.exc_hook, output_handlers=self.handlers)


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
    output_handlers:  t.Sequence[bases.OutputBase] = (DEFAULT_OUTPUT),
    integrations: t.Sequence[bases.Integration] = ()
    ):
    previous = sys.excepthook
    kwargs = {
        "output_handlers": output_handlers,
        "integrations": integrations
    }
    if preserve_previous:
        kwargs["previous_hook"] = previous

    sys.excepthook = partial(excepthook, **kwargs)


capture_exception = HybridContext()

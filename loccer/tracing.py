from __future__ import annotations

import abc
import contextvars
import dataclasses
import functools
import inspect
import random
import time
import uuid
import typing as t
from zlib import adler32

from . import bases
from .ltypes import T_exc_val, T_exc_type, T_exc_tb
from .formats.msgpack import pack as as_msgpack


current_trace: contextvars.ContextVar[t.Optional[Trace]] = contextvars.ContextVar("current_trace", default=None)
current_span: contextvars.ContextVar[t.Optional[Span]] = contextvars.ContextVar("current_span", default=None)


@dataclasses.dataclass
class TracingConfig:
    embed_events: bool = False


current_config: contextvars.ContextVar[TracingConfig] = contextvars.ContextVar("current_config", default=TracingConfig())


class Snapshot(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def snapshot(self) -> dict:
        ...


class Trace(Snapshot):
    def __init__(
            self,
            label: str,
            finished_cb: t.Optional[t.Callable[[Trace], t.Any]]=None,
            sampling: float=1.0
    ) -> None:
        self.id = uuid.uuid4()
        self.label = label
        self.attributes: dict[str, t.Optional[str | int | float]] = {}
        self.__ctx_token: t.Optional[contextvars.Token[t.Optional[Trace]]] = None
        self.children: t.List[Snapshot] = []
        self.start_ts: t.Optional[float] = None
        self.start: t.Optional[float] = None
        self.end: t.Optional[float] = None
        self._finished_cb = finished_cb
        self.sampling = sampling

    def __enter__(self) -> Trace:
        self.start = time.perf_counter_ns()
        self.start_ts = time.time()
        self.__ctx_token = current_trace.set(self)
        return self

    def __exit__(self, exc_type: T_exc_type, exc_val: T_exc_val, exc_tb: T_exc_tb) -> None:
        self.end = time.perf_counter_ns()
        if self.__ctx_token is not None:
            current_trace.reset(self.__ctx_token)

        if self._finished_cb is not None and random.random() <= self.sampling:
            self._finished_cb(self)

    def __call__(self, func):
        def _cb(*args, **kwargs):
            with self.clone():
                return func(*args, **kwargs)

        return _cb

    @property
    def trace(self) -> t.Optional[Trace]:
        return self

    @property
    def as_parent_span(self) -> t.Optional[Span]:
        return None

    @property
    def duration(self) -> t.Optional[float]:
        if self.start is None or self.end is None:
            return None

        return self.end - self.start

    def clone(self) -> Trace:
        return Trace(label=self.label, finished_cb=self._finished_cb)

    def set(self, key: str, value: t.Optional[str | int | float]) -> Trace:
        self.attributes[key] = value
        return self

    def span(self, label: str) -> Span:
        s = Span(label, trace=self.trace, parent=self.as_parent_span)
        return s

    def snapshot(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "attributes": self.attributes,
            "start_ts": self.start_ts,
            "start": self.start,
            "end": self.end,
            "children": [
                x.snapshot() for x in self.children
            ]
        }

    @functools.cached_property
    def ctx_id(self) -> int:
        for x in inspect.stack():
            if x.frame.f_globals.get("__package__") != __package__:
                return self._make_ctx_id(x.frame)

        return 0

    @staticmethod
    def _make_ctx_id(frame) -> int:
        file_name = frame.f_globals.get("__file__", "n/a")
        co_name = frame.f_globals.get("__name__", "n/a")
        co_line = frame.f_lineno

        return Trace.adler_cached(file_name, co_name, co_line)

    @functools.lru_cache(maxsize=None)
    @staticmethod
    def adler_cached(filename, co_name, co_line) -> int:
        return adler32(f"{filename}:{co_name}:{co_line}".encode())


class Span(Trace):
    def __init__(self, label: str, trace: t.Optional[Trace], parent: t.Optional[Span]) -> None:
        super().__init__(label)
        self._trace = trace
        self.parent = parent
        self.__ctx_token: t.Optional[contextvars.Token[t.Optional[Span]]] = None

    def __enter__(self) -> Span:
        self.start_ts = time.time()
        self.start = time.perf_counter_ns()
        self.__ctx_token = current_span.set(self)

        if self.trace is None and (trace:=current_trace.get()) is not None:
            self._trace = trace

        if self.parent is not None:
            self.parent.children.append(self)
        elif self.trace is not None:
            self.trace.children.append(self)

        return self

    def __exit__(self, exc_type: T_exc_type, exc_val: T_exc_val, exc_tb: T_exc_tb) -> None:
        self.end = time.perf_counter_ns()

        if self.__ctx_token is not None:
            current_span.reset(self.__ctx_token)


    @property
    def trace(self) -> t.Optional[Trace]:
        return self._trace

    @property
    def as_parent_span(self) -> t.Optional[Span]:
        return self

    def clone(self) -> Span:
        parent = self.parent
        trace = self.trace

        if (sp:=current_span.get()) is not None:
            parent = sp
            trace = current_trace.get()

        return Span(self.label, trace, parent)

    def snapshot(self) -> dict:
        p = super().snapshot()
        p.pop("start_ts", None)
        if self.parent:
            p["parent"] = self.parent.id
        return p


class Event(Snapshot):
    def __init__(self, event_id: uuid.UUID):
        self.event_id = event_id
        self.start = time.perf_counter_ns()

    @classmethod
    def from_loccer_output(cls, output: bases.LoccerOutput) -> Event:
        return cls(output.id)

    def snapshot(self) -> dict:
        return {"event_id": self.event_id, "start": self.start}


class HybridSpanContext:

    def __new__(cls, label: str) -> Span:
        return make_span(label)

    @classmethod
    def set(cls, key, value) -> t.Type[HybridSpanContext]:
        sp = current_span.get()
        if sp is not None:
            sp.set(key, value)

        return cls


def get_current() -> t.Optional[Trace]:
    if (existing_span := current_span.get()) is not None:
        return existing_span
    elif (existing_trace := current_trace.get()) is not None:
        return existing_trace

    return None


def make_span(label: str) -> Span:
    if (existing:= get_current()) is not None:
        return existing.span(label)
    else:
        return Span(label, trace=None, parent=None)

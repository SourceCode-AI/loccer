from __future__ import annotations

import abc
from abc import ABCMeta, abstractmethod
import datetime
import os
import traceback
import typing as t
import uuid

from .ltypes import T_exc_type, T_exc_val, T_exc_tb, JSONType

if t.TYPE_CHECKING:
    from . import Loccer


class T_Frame(t.TypedDict):
    filename: str
    lineno: t.Optional[int]
    name: str
    line: t.Optional[str]
    locals: t.Optional[dict[str, str]]


class LoccerOutput(metaclass=abc.ABCMeta):
    def __init__(self) -> None:
        self.ts = datetime.datetime.now(datetime.timezone.utc)
        self.integrations_data: dict[str, JSONType] = {}

    @abc.abstractmethod  # pragma: no mutate
    def as_json(self) -> dict[str, JSONType]:
        ...


class ExceptionData(traceback.TracebackException, LoccerOutput):
    def __init__(
        self,
        exc_type: T_exc_type,
        exc_value: T_exc_val,
        exc_traceback: t.Optional[T_exc_tb] = None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(exc_type, exc_value, exc_traceback, **kwargs)
        LoccerOutput.__init__(self)
        self.traceback = exc_traceback

    def as_json(self) -> dict[str, JSONType]:
        data: dict[str, JSONType] = {
            "loccer_type": "exception",
            "timestamp": self.ts.isoformat(),
            "exc_type": self.exc_type.__name__,
            "msg": str(self),
            "integrations": self.integrations_data,
        }

        if self.traceback:
            data["globals"] = {
                name: repr(value)
                for name, value in self.traceback.tb_frame.f_globals.items()
                if name not in ("__builtins__",)
            }

        frames: list[T_Frame] = []

        for frame in self.stack:
            frames.append(frame_as_json(frame))

        data["frames"] = t.cast(JSONType, frames)

        return data


class MetadataLog(LoccerOutput):
    def __init__(self, data: JSONType) -> None:
        super().__init__()
        self.data = data

    def as_json(self) -> dict[str, JSONType]:
        return {
            "loccer_type": "metadata_log",
            "data": self.data,
            "integrations": self.integrations_data,
        }


class OutputBase(metaclass=ABCMeta):
    @abstractmethod  # pragma: no mutate
    def output(self, exc: LoccerOutput, lc: Loccer) -> None:
        ...


class Session(LoccerOutput):
    def __init__(self, lc: Loccer) -> None:
        super().__init__()

        self.session_id: str = str(uuid.uuid4())
        self._session_data: t.Optional[dict[str, JSONType]] = None
        self.captured = False
        self.lc = lc

    @property
    def session_data(self) -> dict[str, JSONType]:
        if self._session_data is None:
            self._session_data = {}
            for x in self.lc.integrations:
                try:
                    sdata = x.session_data()
                    if sdata is not None:
                        self._session_data[x.NAME] = sdata
                except Exception as exc:
                    desc = ["CRITICAL: error while calling the integration to gather data:"] + list(
                        traceback.format_exception(type(exc), exc, exc.__traceback__)
                    )
                    self._session_data[x.NAME] = os.linesep.join(desc)

        return self._session_data

    def as_json(self) -> dict[str, JSONType]:
        return {
            "loccer_type": "session",
            "session_id": self.session_id,
            "data": self.session_data,
        }


class Integration(metaclass=ABCMeta):
    """
    Base class definition for creating loccer integrations
    """

    NAME: t.ClassVar[str]  #: Required class var, name of the integration, must be unique

    def activate(self, loccer_obj: "Loccer") -> None:
        pass

    @abstractmethod  # pragma: no mutate
    def gather(self, context: LoccerOutput) -> JSONType:
        """
        Called when an exception occurred to gather additional data from the integration framework

        :return: Extra data that would be added to the exception context in loccer
        :rtype: JSONType
        """
        ...

    @abstractmethod  # pragma: no mutate
    def session_data(self) -> JSONType:
        ...


def frame_as_json(frame: traceback.FrameSummary) -> T_Frame:
    """
    Reformat traceback frame summary as a json serializable dict

    :param frame: traceback frame summary
    :type frame: traceback.FrameSummary
    :return: json serializable dict
    :rtype: JSONType
    """
    return {
        "filename": frame.filename,
        "lineno": frame.lineno,
        "name": frame.name,
        "line": frame.line,
        "locals": frame.locals,
        # "colno": frame.colno
    }

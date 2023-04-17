import abc
from abc import ABCMeta, abstractmethod
import datetime
import traceback
import typing as t

from .ltypes import T_exc_tb, JSONType


class LoccerOutput(metaclass=abc.ABCMeta):
    def __init__(self):
        self.ts = datetime.datetime.utcnow()
        self.integrations_data: JSONType = {}

    @abc.abstractmethod
    def as_json(self) -> JSONType:
        ...


class ExceptionData(traceback.TracebackException, LoccerOutput):
    def __init__(self, *args, traceback: t.Optional[T_exc_tb]=None, **kwargs):
        super().__init__(*args, **kwargs)
        LoccerOutput.__init__(self)
        self.traceback = traceback

    def as_json(self) -> JSONType:
        data = {
            "loccer_type": "exception",
            "timestamp": self.ts.isoformat(),
            "exc_type": self.exc_type.__name__,
            "msg": str(self),
            "integrations": self.integrations_data,
            "frames": []
        }

        if self.traceback:
            data["globals"] = {name: repr(value) for name, value in self.traceback.tb_frame.f_globals.items() if name not in ("__builtins__",)}

        for frame in self.stack:
            data["frames"].append(frame_as_json(frame))

        return data


class MetadataLog(LoccerOutput):
    def __init__(self, data: JSONType):
        super().__init__()
        self.data = data

    def as_json(self) -> JSONType:
        return {"loccer_type": "metadata_log", "data": self.data, "integrations": self.integrations_data}


class OutputBase(metaclass=ABCMeta):
    @abstractmethod
    def output(self, exc: MetadataLog) -> None:
        ...


class Integration(metaclass=ABCMeta):
    """
    Base class definition for creating loccer integrations
    """
    NAME: t.ClassVar[str]  #: Required class var, name of the integration, must be unique

    @abstractmethod
    def gather(self, context: LoccerOutput) -> JSONType:
        """
        Called when an exception occurred to gather additional data from the integration framework

        :return: Extra data that would be added to the exception context in loccer
        :rtype: JSONType
        """
        ...


def frame_as_json(frame: traceback.FrameSummary) -> JSONType:
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
        #"colno": frame.colno
    }


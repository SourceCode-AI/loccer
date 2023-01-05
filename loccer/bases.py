from abc import ABCMeta, abstractmethod
import datetime
import traceback



class ExceptionData(traceback.TracebackException):
    def __init__(self, *args, traceback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ts = datetime.datetime.utcnow()
        self.traceback = traceback

    def as_json(self) -> dict:
        data = {
            "timestamp": self.ts.isoformat(),
            "exc_type": self.exc_type.__name__,
            "msg": str(self),
            "frames": []
        }

        if self.traceback:
            data["globals"] = {name: repr(value) for name, value in self.traceback.tb_frame.f_globals.items()}

        for frame in self.stack:
            data["frames"].append(frame_as_json(frame))

        return data


class OutputBase(metaclass=ABCMeta):
    @abstractmethod
    def output(self, exc: ExceptionData) -> None:
        ...


def frame_as_json(frame: traceback.FrameSummary):
    return {
        "filename": frame.filename,
        "lineno": frame.lineno,
        "name": frame.name,
        "line": frame.line,
        "locals": frame.locals,
        #"colno": frame.colno
    }


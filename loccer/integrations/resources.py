from __future__ import annotations

import resource
import typing as t

from ..bases import Integration, LoccerOutput
from ..ltypes import JSONType


class T_Usage(t.TypedDict):  # pragma: no mutate
    utime: float
    stime: float
    maxrss: int
    ixrss: int
    idrss: int
    isrss: int
    minflt: int
    majflt: int
    nswap: int
    inblock: int
    oublock: int
    msgsnd: int
    msgrcv: int
    nsignals: int
    nvcsw: int
    nivcsw: int


T_Limits = dict[str, t.Union[tuple[int, int], tuple[float, float]]]  # pragma: no mutate


class T_resources(t.TypedDict):
    limits: T_Limits
    self_usage: T_Usage
    children_usage: T_Usage
    infinity: int | float


class ResourcesIntegration(Integration):
    NAME = "resources"

    def gather(self, context: LoccerOutput) -> JSONType:
        self_usage = self._convert_usage(resource.getrusage(resource.RUSAGE_SELF))
        children_usage = self._convert_usage(resource.getrusage(resource.RUSAGE_CHILDREN))

        limits: T_Limits = {}

        for prop in self.get_props():
            name: str = self.format_prop(prop)
            resource_prop = getattr(resource, prop)
            try:
                limits[name] = resource.getrlimit(resource_prop)
            except (ValueError, OSError):
                pass

        data = {
            "limits": limits,
            "self_usage": self_usage,
            "children_usage": children_usage,
            "infinity": resource.RLIM_INFINITY,
        }
        return t.cast(JSONType, data)

    @staticmethod
    def get_props() -> t.Iterable[str]:
        for prop in dir(resource):
            if prop.startswith("RLIMIT_"):
                yield prop

    def session_data(self) -> JSONType:
        return None

    @staticmethod
    def _convert_usage(usage: resource.struct_rusage) -> T_Usage:
        return {
            "utime": usage.ru_utime,
            "stime": usage.ru_stime,
            "maxrss": usage.ru_maxrss,
            "ixrss": usage.ru_ixrss,
            "idrss": usage.ru_idrss,
            "isrss": usage.ru_isrss,
            "minflt": usage.ru_minflt,
            "majflt": usage.ru_majflt,
            "nswap": usage.ru_nswap,
            "inblock": usage.ru_inblock,
            "oublock": usage.ru_oublock,
            "msgsnd": usage.ru_msgsnd,
            "msgrcv": usage.ru_msgrcv,
            "nsignals": usage.ru_nsignals,
            "nvcsw": usage.ru_nvcsw,
            "nivcsw": usage.ru_nivcsw,
        }

    @staticmethod
    def format_prop(prop: str) -> str:
        idx = -1  # pragma: no mutate
        return prop.split("_", 1)[idx].lower()

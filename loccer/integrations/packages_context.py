from __future__ import annotations

import importlib.metadata
import typing as t

from ..bases import Integration
from ..ltypes import JSONType


if t.TYPE_CHECKING:
    from ..bases import LoccerOutput


class T_EntryPoint(t.TypedDict):
    name: str
    value: str
    group: str


class T_Package(t.TypedDict, total=False):  # pragma: no mutate
    name: str
    version: str
    path: str
    entrypoints: list[T_EntryPoint]


def dump_packages(include_paths: bool = True, include_entry_points: bool = False) -> JSONType:
    data: list[T_Package] = []

    for dist in importlib.metadata.distributions():
        pkg: T_Package = {"name": dist.metadata["Name"], "version": dist.version}

        if include_paths and (pth := getattr(dist, "_path", None)):
            pkg["path"] = str(pth)

        if include_entry_points:
            pkg["entrypoints"] = []

            for x in dist.entry_points:
                pkg["entrypoints"].append({"name": x.name, "value": x.value, "group": x.group})

        data.append(pkg)

    return t.cast(JSONType, data)


class PackagesIntegration(Integration):
    NAME = "packages"

    def __init__(self, include_paths: bool = True, include_entry_points: bool = False) -> None:
        self.include_paths = include_paths
        self.include_entry_points = include_entry_points

    def session_data(self) -> JSONType:
        return dump_packages(
            include_paths=self.include_paths,
            include_entry_points=self.include_entry_points,
        )

    def gather(self, context: LoccerOutput) -> JSONType:
        return None

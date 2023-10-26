from __future__ import annotations

import os
import platform
import site
import typing as t
from getpass import getuser

from ..bases import Integration, LoccerOutput
from ..ltypes import JSONType

if t.TYPE_CHECKING:
    from collections.abc import Collection


DEFAULT_EXCLUDED_ENV_VARS = ("PS1", "VIRTUAL_ENV_PROMPT")  # pragma: no mutate


class T_Uname(t.TypedDict):
    system: str
    node: str
    release: str
    version: str
    machine: str
    processor: str


class T_Python(t.TypedDict):
    compiler: str
    branch: str
    implementation: str
    revision: str
    version: str


class T_Platform(t.TypedDict, total=False):  # pragma: no mutate
    username: str
    hostname: str
    uname: T_Uname
    python: T_Python
    env: dict[str, str]
    site_packages: list[str]
    user_base: str
    user_site_packages: list[str]
    enable_user_site: t.Optional[bool]


class PlatformIntegration(Integration):
    NAME = "platform"

    def __init__(
        self,
        excluded_env_vars: Collection[str] = DEFAULT_EXCLUDED_ENV_VARS,
    ):
        self.excluded_env_vars: set[str] = set(excluded_env_vars)

    def gather(self, context: LoccerOutput) -> None:
        return None

    def session_data(self) -> JSONType:
        uname = platform.uname()

        data: T_Platform = {
            "username": getuser(),
            "hostname": platform.node(),
            "uname": t.cast(T_Uname, uname._asdict()),
            "python": {
                "compiler": platform.python_compiler(),
                "branch": platform.python_branch(),
                "implementation": platform.python_implementation(),
                "revision": platform.python_revision(),
                "version": platform.python_version(),
            },
            "env": {},
            "site_packages": list(site.getsitepackages()),
            "user_base": site.getuserbase(),
            "user_site_packages": list(site.getusersitepackages()),
            "enable_user_site": site.ENABLE_USER_SITE,
        }

        for k, v in os.environ.items():
            if k not in self.excluded_env_vars:
                data["env"][k] = v

        return t.cast(JSONType, data)

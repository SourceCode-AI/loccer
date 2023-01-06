import os
import platform
from getpass import getuser
import typing as t

from ..bases import Integration


class PlatformIntegration(Integration):
    NAME = "platform"

    def gather(self) -> t.Dict[str, t.Any]:
        uname = platform.uname()

        data = {
            "username": getuser(),
            "hostname": platform.node(),
            "uname": uname._asdict(),
            "python": {
                "compiler": platform.python_compiler(),
                "branch": platform.python_branch(),
                "implementation": platform.python_implementation(),
                "revision": platform.python_revision(),
                "version": platform.python_version()
            },
            "environment_variables": dict(os.environ)
        }

        return data

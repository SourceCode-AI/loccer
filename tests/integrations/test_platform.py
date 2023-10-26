import os
import uuid
from unittest.mock import MagicMock, patch

import loccer
from loccer.integrations import platform_context


def test_plaform_session_data():
    ctx = platform_context.PlatformIntegration()
    assert ctx.gather(MagicMock()) is None

    data = ctx.session_data()

    req_keys = (
        "username",
        "hostname",
        "uname",
        "python",
        "python.compiler",
        "python.branch",
        "python.implementation",
        "python.revision",
        "python.version",
        "env",
    )

    for key in req_keys:
        entry = data
        for key_part in key.split("."):
            entry = entry[key_part]
            assert entry is not None

    assert isinstance(data["site_packages"], list)
    assert all(isinstance(x, str) for x in data["site_packages"]), data["site_packages"]
    assert isinstance(data["user_base"], str)
    assert isinstance(data["user_site_packages"], list)
    assert all(isinstance(x, str) for x in data["user_site_packages"]), data["user_site_packages"]
    assert "enable_user_site" in data


def test_platform_integration(in_memory):
    loccer.capture_exception.integrations = (platform_context.PlatformIntegration(),)
    loccer.capture_exception.log_metadata("Test data")

    assert len(in_memory.logs) == 2
    sess = in_memory.logs[0]
    assert "platform" in sess["data"]
    assert isinstance(sess["data"]["platform"], dict)

    log = in_memory.logs[1]
    assert "platform" not in log["data"]


def test_default():
    pint = platform_context.PlatformIntegration()
    assert isinstance(pint.excluded_env_vars, set)
    assert pint.excluded_env_vars == set(platform_context.DEFAULT_EXCLUDED_ENV_VARS)
    assert platform_context.DEFAULT_EXCLUDED_ENV_VARS is not None
    assert len(platform_context.DEFAULT_EXCLUDED_ENV_VARS) > 0


def test_excluded_env_vars():
    value = "pytest"

    env_vars = (str(uuid.uuid4()) for _ in range(10))
    orig_env = set(os.environ.keys())

    with patch.dict("os.environ", {x: value for x in env_vars}):
        pint = platform_context.PlatformIntegration(excluded_env_vars=env_vars)
        sdata = pint.session_data()

        assert all(os.environ[x] == value for x in env_vars)
        assert all(x not in sdata["env"] for x in env_vars)
        assert all(sdata["env"][x] is not None for x in orig_env)

import resource
import sys
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="tests for linux only")


from loccer.integrations import resources as resint


def assert_usage(usage_dict) -> bool:
    expected_keys = {
        "utime",
        "stime",
        "maxrss",
        "ixrss",
        "idrss",
        "isrss",
        "minflt",
        "majflt",
        "nswap",
        "inblock",
        "oublock",
        "msgsnd",
        "msgrcv",
        "nsignals",
        "nvcsw",
        "nivcsw",
    }

    dict_keys = set(usage_dict.keys())
    assert expected_keys == dict_keys

    for key in expected_keys:
        assert isinstance(usage_dict[key], (float, int)), (key, usage_dict)

    return True


@pytest.mark.parametrize("who", (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN))
def test_convert_usage(who) -> None:
    usage = resource.getrusage(who)
    converted = resint.ResourcesIntegration._convert_usage(usage)
    assert assert_usage(converted)


def test_get_props():
    props = tuple(resint.ResourcesIntegration.get_props())
    assert len(props) > 2

    for x in props:
        assert isinstance(x, str)
        assert x.startswith("RLIMIT_")
        assert hasattr(resource, x)


def test_gather():
    integration = resint.ResourcesIntegration()
    assert integration.NAME == "resources"
    ctx = MagicMock()
    output = integration.gather(ctx)

    assert assert_usage(output["self_usage"])
    assert assert_usage(output["children_usage"])
    assert isinstance(output["limits"], dict)
    assert isinstance(output["infinity"], (int, float))

    for x in ("cpu", "rss"):
        assert x in output["limits"]
        limit = output["limits"][x]
        assert isinstance(limit, tuple)
        assert len(limit) == 2
        assert isinstance(limit[0], (int, float))
        assert isinstance(limit[1], (int, float))


@pytest.mark.parametrize(
    "prop, normalized",
    (
        ("RLIMIT_CORE", "core"),
        ("RLIMIT_CPU", "cpu"),
        ("RLIMIT_NOFILE", "nofile"),
        ("RLIMIT_AB_CD", "ab_cd"),
    ),
)
def test_format_prop(prop, normalized):
    output = resint.ResourcesIntegration.format_prop(prop)
    assert output == normalized

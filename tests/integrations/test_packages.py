import importlib.metadata
from unittest.mock import patch, MagicMock

import pytest

from loccer.integrations import packages_context


def test_integration_defaults():
    pint = packages_context.PackagesIntegration()
    assert pint.NAME == "packages"
    assert pint.include_paths is True
    assert pint.include_entry_points is False
    assert pint.gather(MagicMock()) is None

    output = packages_context.dump_packages()

    for pkg in output:
        assert "path" in pkg
        assert "entrypoints" not in pkg


@pytest.mark.parametrize("paths,entrypoints", ((True, True), (True, False), (False, True), (False, False)))
def test_integration_options(paths, entrypoints):
    pint = packages_context.PackagesIntegration(include_paths=paths, include_entry_points=entrypoints)

    with patch("loccer.integrations.packages_context.dump_packages") as m:
        pint.session_data()
        m.assert_called_once_with(include_paths=paths, include_entry_points=entrypoints)


def test_pkg_output():
    packages = packages_context.dump_packages(include_paths=True, include_entry_points=True)
    assert isinstance(packages, list)
    assert len(packages) > 0

    for pkg in packages:
        if pkg["name"] == "pytest":
            assert isinstance(pkg["version"], str)
            assert isinstance(pkg["path"], str)
            assert len(pkg["entrypoints"]) > 0
            for e in pkg["entrypoints"]:
                assert isinstance(e["name"], str)
                assert isinstance(e["value"], str)
                assert isinstance(e["group"], str)
            break
    else:
        raise RuntimeError("Can't find pytest package information")

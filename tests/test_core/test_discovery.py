"""Discovery and metadata tests."""

from __future__ import annotations

import pytest

from apiforge.core.discovery import PluginRegistry
from apiforge.core.exceptions import PluginNotFoundError
from apiforge.core.metadata import AuthType, OperationMetadata, PluginMetadata


def test_registry_contains(fake_plugin_class) -> None:
    reg = PluginRegistry()
    reg._factories = {"fake": fake_plugin_class}
    reg._discovered = True
    assert "fake" in reg
    assert len(reg) == 1


def test_registry_get_returns_class(fake_plugin_class) -> None:
    reg = PluginRegistry()
    reg._factories = {"fake": fake_plugin_class}
    reg._discovered = True
    assert reg.get("fake") is fake_plugin_class


def test_registry_get_missing_raises(fake_plugin_class) -> None:
    reg = PluginRegistry()
    reg._factories = {"fake": fake_plugin_class}
    reg._discovered = True
    with pytest.raises(PluginNotFoundError):
        reg.get("nope")


def test_metadata_is_frozen() -> None:
    meta = PluginMetadata(name="x", version="0.1.0")
    with pytest.raises(Exception):  # noqa: B017
        meta.name = "y"  # type: ignore[misc]


def test_metadata_alias_async() -> None:
    op = OperationMetadata(name="x", **{"async": False})  # type: ignore[arg-type]
    assert op.async_ is False


def test_metadata_rejects_extra() -> None:
    with pytest.raises(Exception):  # noqa: B017
        PluginMetadata(name="x", version="0.1.0", bogus="field")  # type: ignore[call-arg]


def test_auth_type_values() -> None:
    assert AuthType.TOKEN.value == "token"
    assert AuthType.OAUTH2.value == "oauth2"

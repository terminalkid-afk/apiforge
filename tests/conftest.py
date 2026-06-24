"""Shared pytest fixtures."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from apiforge.core.client import APIForge
from apiforge.core.config import APIForgeConfig
from apiforge.core.credentials import CredentialManager
from apiforge.core.discovery import PluginRegistry
from apiforge.core.metadata import AuthType, OperationMetadata, PluginMetadata
from apiforge.plugins.base import BasePlugin


class _FakePlugin(BasePlugin):
    """A minimal plugin used by tests.

    Returns a deterministic value from ``echo`` and counts calls.
    The plugin's ``metadata`` is real (it has to be valid Pydantic)
    so the CLI and registry tests can run against it.
    """

    metadata = PluginMetadata(
        name="fake",
        version="0.0.1",
        description="Test plugin.",
        auth_type=AuthType.TOKEN,
        operations=(OperationMetadata(name="echo", description="Echo back the input."),),
    )

    calls: ClassVar[list[dict[str, Any]]] = []

    async def setup(self) -> None:
        return None

    async def echo(self, value: str) -> str:
        type(self).calls.append({"method": "echo", "value": value})
        return value


@pytest.fixture
def fake_plugin_class() -> type[_FakePlugin]:
    """Return the fake plugin class (not an instance)."""
    _FakePlugin.calls = []  # reset
    return _FakePlugin


@pytest.fixture
def registry(fake_plugin_class: type[BasePlugin]) -> PluginRegistry:
    """A registry that contains only the fake plugin.

    Avoids depending on whatever entry points happen to be installed
    in the test environment.
    """
    reg = PluginRegistry()
    # Inject directly so we don't depend on the installed entry points.
    reg._factories = {"fake": fake_plugin_class}
    reg._discovered = True
    return reg


@pytest.fixture
def credentials() -> CredentialManager:
    """A CredentialManager that ignores the on-disk config file.

    Tests should not be able to pick up developer-local secrets.
    """
    from pathlib import Path

    return CredentialManager(config_path=Path("/nonexistent/apiforge.toml"))


@pytest.fixture
def config() -> APIForgeConfig:
    return APIForgeConfig(timeout=5.0, max_retries=0, verify_ssl=False)


@pytest.fixture
def client(
    config: APIForgeConfig,
    credentials: CredentialManager,
    registry: PluginRegistry,
) -> APIForge:
    """A wired-up :class:`APIForge` with no real plugins installed."""
    return APIForge(config=config, credentials=credentials, registry=registry)

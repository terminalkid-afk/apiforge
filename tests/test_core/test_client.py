"""Tests for the unified APIForge client."""

from __future__ import annotations

import pytest

from apiforge import APIForge
from apiforge.core.exceptions import PluginNotFoundError


def test_client_lists_registered_plugins(client: APIForge) -> None:
    assert client.list_plugins() == ["fake"]


def test_client_attribute_access_instantiates_plugin(client: APIForge) -> None:
    # The first access should work transparently through the SyncProxy.
    result = client.fake.echo(value="hello")
    assert result == "hello"


def test_unknown_attribute_raises_helpful_error(client: APIForge) -> None:
    with pytest.raises(AttributeError) as exc_info:
        _ = client.does_not_exist
    assert "does_not_exist" in str(exc_info.value)
    # The error mentions the available plugin so users can self-correct.
    assert "fake" in str(exc_info.value)


def test_get_plugin_returns_instance(client: APIForge) -> None:
    p1 = client.get_plugin("fake")
    p2 = client.get_plugin("fake")
    # Same instance — the registry caches.
    assert p1 is p2


def test_get_plugin_missing_raises(client: APIForge) -> None:
    with pytest.raises(PluginNotFoundError):
        client.get_plugin("missing")


@pytest.mark.asyncio
async def test_client_async_context_manager(client: APIForge) -> None:
    async with client as c:
        plugin = c.get_plugin("fake")
        assert plugin.name == "fake"


@pytest.mark.asyncio
async def test_close_is_idempotent(client: APIForge) -> None:
    await client.close()
    await client.close()  # should not raise


def test_configure_strips_token_suffix(client: APIForge) -> None:
    client.configure(github_token="ghp_abc")
    assert client.credentials.get("github") == "ghp_abc"


def test_configure_keeps_bare_name(client: APIForge) -> None:
    client.configure(notion="secret_xyz")
    assert client.credentials.get("notion") == "secret_xyz"

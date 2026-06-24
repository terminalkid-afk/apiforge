"""Tests for the bundled first-party plugins."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from apiforge.plugins.discord import DISCORD_API, DiscordPlugin
from apiforge.plugins.github import GITHUB_API, GitHubPlugin
from apiforge.plugins.notion import NOTION_API, NOTION_VERSION, NotionPlugin


def _make_client(plugin_class, token: str = "test-token"):  # noqa: S107
    """Build a minimal client for plugin tests with the given plugin pre-registered."""
    from apiforge.core.client import APIForge
    from apiforge.core.config import APIForgeConfig
    from apiforge.core.credentials import CredentialManager
    from apiforge.core.discovery import PluginRegistry

    cfg = APIForgeConfig(timeout=5.0, verify_ssl=False)
    creds = CredentialManager(config_path=__import__("pathlib").Path("/nonexistent"))
    creds.set(plugin_class.metadata.name, token)
    reg = PluginRegistry()
    reg._factories = {plugin_class.metadata.name: plugin_class}
    reg._discovered = True
    return APIForge(config=cfg, credentials=creds, registry=reg)


# ---------------------------------------------------------------------- GitHub


@pytest.mark.asyncio
@respx.mock
async def test_github_get_user() -> None:
    respx.get(f"{GITHUB_API}/users/octocat").mock(
        return_value=Response(200, json={"login": "octocat", "id": 1})
    )
    client = _make_client(GitHubPlugin, token="ghp_xxx")
    plugin = client.get_plugin("github")
    user = await plugin.get_user("octocat")
    assert user["login"] == "octocat"


@pytest.mark.asyncio
@respx.mock
async def test_github_list_repos_truncates() -> None:
    payload = [{"name": f"r{i}"} for i in range(50)]
    respx.get(f"{GITHUB_API}/users/octocat/repos").mock(return_value=Response(200, json=payload))
    client = _make_client(GitHubPlugin)
    plugin = client.get_plugin("github")
    repos = await plugin.list_repos("octocat", limit=10)
    assert len(repos) == 10


@pytest.mark.asyncio
async def test_github_create_issue_requires_credential() -> None:
    client = _make_client(GitHubPlugin)  # no token
    client.credentials._store.explicit.clear()  # remove the token
    plugin = client.get_plugin("github")
    with pytest.raises(Exception):  # noqa: B017
        await plugin.create_issue("x", "y", "title")


# ---------------------------------------------------------------------- Discord


@pytest.mark.asyncio
@respx.mock
async def test_discord_send_message() -> None:
    respx.post(f"{DISCORD_API}/channels/123/messages").mock(
        return_value=Response(200, json={"id": "1", "content": "hi"})
    )
    client = _make_client(DiscordPlugin)
    plugin = client.get_plugin("discord")
    msg = await plugin.send_message("123", "hi")
    assert msg["content"] == "hi"


@pytest.mark.asyncio
@respx.mock
async def test_discord_list_guilds() -> None:
    respx.get(f"{DISCORD_API}/users/@me/guilds").mock(
        return_value=Response(200, json=[{"id": "1", "name": "g"}])
    )
    client = _make_client(DiscordPlugin)
    plugin = client.get_plugin("discord")
    guilds = await plugin.list_guilds()
    assert guilds == [{"id": "1", "name": "g"}]


# ---------------------------------------------------------------------- Notion


@pytest.mark.asyncio
@respx.mock
async def test_notion_list_pages() -> None:
    respx.post(f"{NOTION_API}/search").mock(
        return_value=Response(200, json={"results": [{"id": "p1"}]})
    )
    client = _make_client(NotionPlugin)
    plugin = client.get_plugin("notion")
    pages = await plugin.list_pages()
    assert pages == [{"id": "p1"}]


@pytest.mark.asyncio
@respx.mock
async def test_notion_auth_header_includes_version() -> None:
    route = respx.post(f"{NOTION_API}/search").mock(
        return_value=Response(200, json={"results": []})
    )
    client = _make_client(NotionPlugin)
    plugin = client.get_plugin("notion")
    await plugin.list_pages()
    sent = route.calls.last.request
    assert sent.headers["Notion-Version"] == NOTION_VERSION
    assert sent.headers["Authorization"] == "Bearer test-token"

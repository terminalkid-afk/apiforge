"""Discord plugin.

Covers a tiny but useful slice: sending a message to a channel and
listing guilds the bot is a member of. The real Discord SDK has
hundreds of operations; this plugin is intentionally narrow.
"""

from __future__ import annotations

from typing import Any

from apiforge.core.metadata import AuthType, OperationMetadata, PluginMetadata
from apiforge.plugins.base import BasePlugin

DISCORD_API = "https://discord.com/api/v10"


class DiscordPlugin(BasePlugin):
    """Plugin for the Discord REST API (bot token auth)."""

    metadata = PluginMetadata(
        name="discord",
        version="0.1.0",
        description="Discord bot API: send messages, list guilds and channels.",
        auth_type=AuthType.TOKEN,
        base_url=DISCORD_API,
        operations=(
            OperationMetadata(
                name="send_message",
                description="Post a message to a channel.",
                parameters={"channel_id": "str", "content": "str"},
            ),
            OperationMetadata(
                name="list_guilds",
                description="List guilds the bot is a member of.",
                parameters={},
            ),
            OperationMetadata(
                name="list_channels",
                description="List channels in a guild.",
                parameters={"guild_id": "str"},
            ),
        ),
    )

    # ------------------------------------------------------------------ lifecycle

    async def setup(self) -> None:
        _ = self.get_credential()  # token presence is opportunistic here

    # ------------------------------------------------------------------ operations

    async def send_message(self, channel_id: str, content: str) -> dict[str, Any]:
        """POST a message to a channel.

        ``POST /channels/{channel_id}/messages``
        """
        token = self.require_credential()
        response = await self.http.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            json={"content": content},
            headers={"Authorization": f"Bot {token}"},
        )
        response.raise_for_status()
        message: dict[str, Any] = response.json()
        return message

    async def list_guilds(self) -> list[dict[str, Any]]:
        """List guilds the bot is in."""
        token = self.require_credential()
        response = await self.http.get(
            f"{DISCORD_API}/users/@me/guilds",
            headers={"Authorization": f"Bot {token}"},
        )
        response.raise_for_status()
        guilds: list[dict[str, Any]] = response.json()
        return guilds

    async def list_channels(self, guild_id: str) -> list[dict[str, Any]]:
        """List channels in a guild."""
        token = self.require_credential()
        response = await self.http.get(
            f"{DISCORD_API}/guilds/{guild_id}/channels",
            headers={"Authorization": f"Bot {token}"},
        )
        response.raise_for_status()
        channels: list[dict[str, Any]] = response.json()
        return channels

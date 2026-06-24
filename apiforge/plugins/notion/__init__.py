"""Notion plugin.

A small wrapper around the Notion API: list databases, query a
database, and list pages. Notion uses a bearer token (the "internal
integration" secret) plus a `Notion-Version` header.
"""

from __future__ import annotations

from typing import Any

from apiforge.core.metadata import AuthType, OperationMetadata, PluginMetadata
from apiforge.plugins.base import BasePlugin

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionPlugin(BasePlugin):
    """Plugin for the Notion REST API."""

    metadata = PluginMetadata(
        name="notion",
        version="0.1.0",
        description="Notion API: list and query pages, databases, blocks.",
        auth_type=AuthType.TOKEN,
        base_url=NOTION_API,
        operations=(
            OperationMetadata(
                name="list_pages",
                description="List pages the integration has access to.",
                parameters={"limit": "int"},
            ),
            OperationMetadata(
                name="list_databases",
                description="List databases the integration has access to.",
                parameters={"limit": "int"},
            ),
            OperationMetadata(
                name="query_database",
                description="Query a Notion database with a filter.",
                parameters={"database_id": "str", "filter": "dict"},
            ),
        ),
    )

    # ------------------------------------------------------------------ lifecycle

    async def setup(self) -> None:
        _ = self.get_credential()

    # ------------------------------------------------------------------ operations

    async def list_pages(self, limit: int = 50) -> list[dict[str, Any]]:
        """List pages. Notion's API returns paged envelopes; we flatten."""
        token = self.require_credential()
        response = await self.http.post(
            f"{NOTION_API}/search",
            json={"filter": {"property": "object", "value": "page"}, "page_size": limit},
            headers=self._auth_headers(token),
        )
        response.raise_for_status()
        payload = response.json()
        return list(payload.get("results", []))

    async def list_databases(self, limit: int = 50) -> list[dict[str, Any]]:
        """List databases. Same shape as pages; we filter by object type."""
        token = self.require_credential()
        response = await self.http.post(
            f"{NOTION_API}/search",
            json={"filter": {"property": "object", "value": "database"}, "page_size": limit},
            headers=self._auth_headers(token),
        )
        response.raise_for_status()
        payload = response.json()
        return list(payload.get("results", []))

    async def query_database(
        self,
        database_id: str,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run a query against a Notion database."""
        token = self.require_credential()
        body: dict[str, Any] = {}
        if filter is not None:
            body["filter"] = filter
        response = await self.http.post(
            f"{NOTION_API}/databases/{database_id}/query",
            json=body,
            headers=self._auth_headers(token),
        )
        response.raise_for_status()
        payload = response.json()
        return list(payload.get("results", []))

    # ------------------------------------------------------------------ helpers

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

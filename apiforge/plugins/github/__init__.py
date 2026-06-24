"""GitHub plugin.

Covers the most common operations: fetching users, listing repos, and
creating issues. The plugin is intentionally minimal — it shows the
shape of a real plugin without trying to wrap the full GitHub API.
"""

from __future__ import annotations

from typing import Any

from apiforge.core.metadata import AuthType, OperationMetadata, PluginMetadata
from apiforge.plugins.base import BasePlugin

GITHUB_API = "https://api.github.com"


class GitHubPlugin(BasePlugin):
    """Plugin for the GitHub REST API."""

    metadata = PluginMetadata(
        name="github",
        version="0.1.0",
        description="Interact with the GitHub REST API (users, repos, issues).",
        auth_type=AuthType.TOKEN,
        base_url=GITHUB_API,
        operations=(
            OperationMetadata(
                name="get_user",
                description="Fetch a GitHub user profile by login name.",
                parameters={"username": "str"},
            ),
            OperationMetadata(
                name="list_repos",
                description="List public repositories for a user.",
                parameters={"username": "str", "limit": "int"},
            ),
            OperationMetadata(
                name="create_issue",
                description="Create an issue on a repository.",
                parameters={"owner": "str", "repo": "str", "title": "str", "body": "str"},
            ),
        ),
        openapi_url="https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
    )

    # ------------------------------------------------------------------ lifecycle

    async def setup(self) -> None:
        """Validate that a token is present.

        We don't make a network call here; the user's first real
        request will fail with a clear error if the token is wrong.
        """
        # ``get_credential`` returns None for missing — that's fine.
        # We deliberately do NOT raise, so the user can list operations
        # even without credentials.
        _ = self.get_credential()

    # ------------------------------------------------------------------ operations

    async def get_user(self, username: str) -> dict[str, Any]:
        """Fetch a GitHub user by login.

        ``GET https://api.github.com/users/{username}``
        """
        response = await self.http.get(
            f"{GITHUB_API}/users/{username}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def list_repos(self, username: str, limit: int = 30) -> list[dict[str, Any]]:
        """List public repos for ``username``.

        ``limit`` is enforced client-side; the GitHub API paginates.
        """
        response = await self.http.get(
            f"{GITHUB_API}/users/{username}/repos",
            params={"per_page": min(limit, 100), "type": "public"},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        repos: list[dict[str, Any]] = response.json()
        return repos[:limit]

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
    ) -> dict[str, Any]:
        """Create an issue. Requires authentication."""
        token = self.require_credential()
        response = await self.http.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues",
            json={"title": title, "body": body},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response.raise_for_status()
        issue: dict[str, Any] = response.json()
        return issue

    # ------------------------------------------------------------------ helpers

    def _auth_headers(self) -> dict[str, str]:
        """Common GitHub headers, including auth if a token is present."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = self.get_credential()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

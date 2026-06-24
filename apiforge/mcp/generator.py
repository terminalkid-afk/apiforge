"""MCP server generator — Phase 4 deliverable.

The generator walks the plugin registry, asks each plugin for its
:class:`~apiforge.mcp.adapter.BaseMCPAdapter` (or falls back to a
default), and assembles a single MCP server description.

This is a TODO for Phase 4. The interface is in place so the CLI can
already wire the command, and so plugin authors can write adapters
against a stable contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from apiforge.mcp.adapter import BaseMCPAdapter

if TYPE_CHECKING:
    from apiforge.core.client import APIForge


class MCPGenerator:
    """Build MCP server manifests from an :class:`APIForge` client.

    The class is small on purpose: it composes adapters and serializes
    their output. The interesting work — translating Python type
    annotations into JSON Schema — happens in the adapter.
    """

    def __init__(self, client: APIForge) -> None:
        self._client = client

    # ------------------------------------------------------------------ public

    def generate(self, plugin_names: list[str] | None = None) -> dict[str, Any]:
        """Generate a complete MCP server manifest.

        If ``plugin_names`` is ``None``, every registered plugin is
        included. Otherwise the named subset is generated.
        """
        names = plugin_names or self._client.list_plugins()
        servers: list[dict[str, Any]] = []
        for name in names:
            plugin = self._client.get_plugin(name)
            adapter = self._adapter_for(plugin)
            servers.append(adapter.to_mcp_server())
        return {
            "$schema": "https://apiforge.dev/schemas/mcp-server/v1.json",
            "version": "0.1.0",
            "servers": servers,
        }

    def write(self, target: str, plugin_names: list[str] | None = None) -> None:
        """Generate and write to ``target`` (file path or ``'-'`` for stdout).

        TODO[Phase 4]: Implement serialization and filesystem write.
        """
        manifest = self.generate(plugin_names)
        # TODO[Phase 4]: Replace with proper JSON/YAML writer.
        import json

        if target == "-":
            print(json.dumps(manifest, indent=2))
        else:
            with Path(target).open("w", encoding="utf-8") as fh:
                json.dump(manifest, fh, indent=2)

    # ------------------------------------------------------------------ helpers

    def _adapter_for(self, plugin: Any) -> BaseMCPAdapter:
        """Look up the plugin's MCP adapter.

        TODO[Phase 4]: Plugins should declare ``MCP_ADAPTER_CLASS`` on
        the plugin class, e.g.::

            class GitHubPlugin(BasePlugin):
                MCP_ADAPTER_CLASS = GitHubMCPAdapter

        For now we fall back to a NotImplementedError so the
        generator's contract is exercisable.
        """
        adapter_cls = getattr(plugin, "MCP_ADAPTER_CLASS", None)
        if adapter_cls is None:
            msg = (
                f"Plugin '{plugin.name}' has no MCP_ADAPTER_CLASS. "
                "Phase 4 will add a default adapter that reads type hints."
            )
            raise NotImplementedError(msg)
        return adapter_cls(plugin)

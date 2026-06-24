"""Base class for MCP adapters.

A plugin that wants to be exposed as an MCP tool implements a subclass
of :class:`BaseMCPAdapter` and ships it next to the plugin class. The
:class:`MCPGenerator` then walks the plugin registry and uses each
adapter to produce a tool schema.

Why an adapter rather than a generator that reads the plugin class
directly? The plugin surface is a Python API: methods, defaults,
type-erased arguments. MCP needs a *declarative* description: tool
names, JSON-Schema parameters, and a dispatch table. The adapter is
the boundary between the imperative plugin and the declarative tool
description.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apiforge.core.metadata import PluginMetadata
    from apiforge.plugins.base import BasePlugin


class BaseMCPAdapter(ABC):
    """Translate a plugin into MCP tool definitions.

    Subclasses must implement :meth:`tool_definitions`. The default
    implementations of :meth:`dispatch` and :meth:`list_tools` work
    for the common case where the adapter is constructed with a
    plugin instance.
    """

    def __init__(self, plugin: BasePlugin) -> None:
        self._plugin = plugin

    @property
    def plugin(self) -> BasePlugin:
        return self._plugin

    @property
    def metadata(self) -> PluginMetadata:
        return self._plugin.metadata

    # ------------------------------------------------------------------ contract

    @abstractmethod
    def tool_definitions(self) -> list[dict[str, Any]]:
        """Return MCP tool definitions for this plugin.

        Each tool definition has the shape::

            {
                "name": "github__get_user",
                "description": "Fetch a GitHub user by login.",
                "inputSchema": { ... JSON Schema ... }
            }
        """
        raise NotImplementedError

    async def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Invoke a tool by name and return the result.

        The default implementation splits the tool name on ``__`` to
        get the plugin and operation names, then calls the plugin
        method. Subclasses may override for more sophisticated routing.
        """
        parts = tool_name.split("__", 1)
        if len(parts) != 2 or parts[0] != self.metadata.name:
            msg = f"Tool '{tool_name}' is not handled by adapter for '{self.metadata.name}'"
            raise ValueError(msg)
        _, op = parts
        method = getattr(self._plugin, op, None)
        if method is None or not callable(method):
            msg = f"Plugin '{self.metadata.name}' has no operation '{op}'"
            raise AttributeError(msg)
        return await method(**arguments)

    # ------------------------------------------------------------------ convenience

    def list_tools(self) -> list[str]:
        """Return the names of tools this adapter exposes."""
        return [tool["name"] for tool in self.tool_definitions()]

    def to_mcp_server(self) -> dict[str, Any]:
        """Serialize to an MCP server manifest (JSON-ready)."""
        return {
            "name": self.metadata.name,
            "version": self.metadata.version,
            "tools": self.tool_definitions(),
        }

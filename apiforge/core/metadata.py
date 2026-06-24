"""Plugin metadata — the contract every plugin publishes.

This module defines the schema a plugin uses to describe itself.
A consistent schema is what lets ``apiforge plugins`` list everything,
``apiforge info <name>`` show details, and (later) an MCP generator
walk the plugin registry without knowing the plugin's internals.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class AuthType(StrEnum):
    """How a plugin authenticates with its upstream service."""

    TOKEN = "token"  # noqa: S105
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    NONE = "none"


class OperationMetadata(BaseModel, frozen=True):
    """A single operation exposed by a plugin.

    Operations are the plugin's named methods; the schema here lets the
    CLI, the OpenAPI generator, and the MCP generator inspect them
    without instantiating the plugin.
    """

    name: str = Field(description="Operation name, e.g. 'get_user'")
    description: str = Field(default="", description="Human-readable summary")
    async_: bool = Field(
        default=True,
        alias="async",
        description="Whether the underlying implementation is async.",
    )
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Name → type map of operation parameters.",
    )


class PluginMetadata(BaseModel, frozen=True):
    """Self-describing metadata for a plugin.

    Every plugin publishes this. ``APIForge`` reads it at registration
    time to populate the CLI, the registry, and (later) generators.
    """

    name: str = Field(description="Unique plugin identifier, e.g. 'github'")
    version: str = Field(description="Plugin semver, e.g. '0.1.0'")
    description: str = Field(default="", description="Short plugin description")
    auth_type: AuthType = Field(
        default=AuthType.TOKEN,
        description="Authentication strategy this plugin expects.",
    )
    base_url: str | None = Field(
        default=None,
        description="Default upstream base URL; some plugins are not URL-based.",
    )
    operations: tuple[OperationMetadata, ...] = Field(
        default_factory=tuple,
        description="Operations this plugin exposes.",
    )
    openapi_url: str | None = Field(
        default=None,
        description="URL to an OpenAPI spec, if available.",
    )

    model_config = {"extra": "forbid"}


# Literal type for use in function signatures — preferred over ``str``.
AuthTypeLiteral = Literal["token", "api_key", "oauth2", "basic", "none"]

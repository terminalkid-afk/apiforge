"""APIForge — Unified interface for multiple APIs.

A plugin-based framework that provides a single, consistent Python API for
interacting with many external services (GitHub, Discord, Notion, and many
more). Authentication, HTTP transport, and plugin discovery are handled
centrally so individual plugins can focus on the service-specific surface.
"""

from apiforge.core.client import APIForge
from apiforge.core.config import APIForgeConfig
from apiforge.core.credentials import CredentialManager
from apiforge.core.discovery import PluginRegistry
from apiforge.core.exceptions import (
    APIForgeError,
    AuthenticationError,
    PluginError,
    PluginNotFoundError,
    RateLimitError,
)
from apiforge.core.metadata import AuthType, OperationMetadata, PluginMetadata
from apiforge.plugins.base import BasePlugin

__version__ = "0.1.0"

__all__ = [
    "APIForge",
    "APIForgeConfig",
    "APIForgeError",
    "AuthType",
    "AuthenticationError",
    "BasePlugin",
    "CredentialManager",
    "OperationMetadata",
    "PluginError",
    "PluginMetadata",
    "PluginNotFoundError",
    "PluginRegistry",
    "RateLimitError",
    "__version__",
]

"""Core abstractions: configuration, credentials, discovery, errors."""

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
from apiforge.core.metadata import AuthType, PluginMetadata

__all__ = [
    "APIForge",
    "APIForgeConfig",
    "APIForgeConfig",
    "APIForgeError",
    "AuthType",
    "AuthenticationError",
    "CredentialManager",
    "PluginError",
    "PluginMetadata",
    "PluginNotFoundError",
    "PluginRegistry",
    "RateLimitError",
]

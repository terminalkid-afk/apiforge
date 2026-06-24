"""Exception hierarchy.

A small, focused set of errors that any caller can pattern-match on.
Plugins should raise these (or subclasses) so user code can catch a
single ``APIForgeError`` and still discriminate by type.
"""

from __future__ import annotations


class APIForgeError(Exception):
    """Base exception for all APIForge errors."""

    def __init__(self, message: str, *, plugin: str | None = None) -> None:
        super().__init__(message)
        self.plugin = plugin


class PluginError(APIForgeError):
    """Raised when a plugin fails to operate correctly."""


class PluginNotFoundError(APIForgeError):
    """Raised when a requested plugin name is not registered."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Plugin '{name}' is not registered", plugin=name)
        self.name = name


class AuthenticationError(APIForgeError):
    """Raised when authentication fails or credentials are missing."""


class RateLimitError(APIForgeError):
    """Raised when an upstream service rate-limits the request.

    Attributes:
        retry_after: Seconds the server told us to wait, if it told us.
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: float | None = None,
        plugin: str | None = None,
    ) -> None:
        super().__init__(message, plugin=plugin)
        self.retry_after = retry_after


class ConfigurationError(APIForgeError):
    """Raised when configuration is invalid or incomplete."""


class TransportError(APIForgeError):
    """Raised when the HTTP transport itself fails (timeout, connection, etc)."""

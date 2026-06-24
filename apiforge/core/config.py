"""Runtime configuration for APIForge.

We use ``pydantic-settings`` so that configuration can be supplied via:

1. ``APIForge.configure(...)`` keyword arguments (highest priority)
2. Environment variables prefixed with ``APIFORGE_``
3. A ``.env`` file in the working directory

This layered approach lets scripts and libraries configure explicitly,
while deployed processes (CI, containers) work via environment without
any code changes.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIForgeConfig(BaseSettings):
    """Global configuration shared by the client and all plugins.

    Per-plugin credentials live on :class:`~apiforge.core.credentials.CredentialManager`,
    not here — this object holds cross-cutting knobs (timeouts, retries,
    log level) that affect every plugin uniformly.
    """

    model_config = SettingsConfigDict(
        env_prefix="APIFORGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    timeout: float = Field(
        default=30.0,
        description="Default HTTP timeout in seconds for plugin requests.",
        gt=0,
    )
    max_retries: int = Field(
        default=3,
        description="Default number of retries for transient failures.",
        ge=0,
    )
    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify upstream TLS certificates.",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR).",
    )
    user_agent: str = Field(
        default="apiforge/0.1.0",
        description="User-Agent header sent on every request.",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form key/value bag for plugin-specific settings.",
    )

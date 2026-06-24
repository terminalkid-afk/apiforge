"""Common base class for every plugin.

A plugin is a *class*, not an instance — the registry holds factories.
The :class:`APIForge` client instantiates plugins on demand and injects
shared state (HTTP client, credentials, config). Subclasses define the
plugin-specific surface as plain Python methods.

Async is the default: every operation in the base class is declared
``async`` so plugins naturally compose with ``asyncio.gather``. Sync
callers go through the small wrapper the client provides.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

import httpx

from apiforge.core.metadata import PluginMetadata

if TYPE_CHECKING:
    from apiforge.core.client import APIForge


class BasePlugin(ABC):
    """Base class for all APIForge plugins.

    Subclasses must:

    1. Set the :attr:`metadata` class attribute (an instance of
       :class:`PluginMetadata`).
    2. Define their operations as public methods.

    The class does not own long-lived state — it receives a reference
    to the parent :class:`APIForge` client and reaches through it for
    shared resources (the HTTP client, the credential manager, the
    config). This keeps plugins testable in isolation.
    """

    metadata: ClassVar[PluginMetadata]
    """Plugin metadata. Subclasses MUST override this."""

    def __init__(self, client: APIForge) -> None:
        self._client = client

    # ------------------------------------------------------------------ accessors

    @property
    def http(self) -> httpx.AsyncClient:
        """The shared :class:`httpx.AsyncClient` provided by the parent client."""
        return self._client.http

    @property
    def name(self) -> str:
        """Short identifier for the plugin, from :attr:`metadata`."""
        return self.metadata.name

    def get_credential(self, key: str | None = None) -> str | None:
        """Look up a credential for this plugin.

        ``key`` defaults to the plugin name, which is the convention
        every first-party plugin follows. Plugins that need multiple
        credentials (e.g. OAuth client_id + client_secret) can pass
        a sub-key.
        """
        return self._client.credentials.get(key or self.name)

    def require_credential(self, key: str | None = None) -> str:
        """Like :meth:`get_credential` but raises :class:`AuthenticationError`."""
        return self._client.credentials.require(key or self.name)

    # ------------------------------------------------------------------ extension hooks

    @abstractmethod
    async def setup(self) -> None:
        """Hook for one-time async initialization.

        Plugins that need to validate credentials or warm caches on
        first use should override this. The :class:`APIForge` client
        calls it the first time a plugin is accessed.
        """
        raise NotImplementedError

    async def teardown(self) -> None:
        """Hook for clean shutdown. Default: no-op.

        Plugins that hold their own resources (a websocket, a cache)
        should release them here. The client calls this for every
        instantiated plugin when the client itself is closed.
        """
        return

    # ------------------------------------------------------------------ ergonomics

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r} version={self.metadata.version}>"

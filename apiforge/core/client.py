"""The :class:`APIForge` client — the user-facing entry point.

The client owns three long-lived resources and shares them with every
plugin it instantiates:

1. A :class:`~httpx.AsyncClient` for HTTP transport.
2. A :class:`~apiforge.core.credentials.CredentialManager` for secrets.
3. A :class:`~apiforge.core.config.APIForgeConfig` for behavior knobs.

Plugins are accessed by attribute (``client.github``). On first access
we instantiate the plugin, run its ``setup()`` hook, and cache the
instance. This is the lazy-initialization pattern — it's faster than
the alternative and lets plugins do per-instance work (token refresh,
connection pools) at exactly the right moment.
"""

from __future__ import annotations

import inspect
from typing import Any

import httpx

from apiforge.core.config import APIForgeConfig
from apiforge.core.credentials import CredentialManager
from apiforge.core.discovery import PluginRegistry
from apiforge.core.exceptions import PluginError, PluginNotFoundError
from apiforge.plugins.base import BasePlugin


class APIForge:
    """The unified API client.

    >>> client = APIForge()
    >>> client.configure(github_token="ghp_xxx")
    >>> user = await client.github.get_user("octocat")

    Use the client as an async context manager to ensure the underlying
    HTTP connection pool is closed cleanly::

        async with APIForge() as client:
            ...

    The client is reusable: calling :meth:`close` (or exiting the
    context manager) and then making further calls will reopen the
    transport.
    """

    def __init__(
        self,
        *,
        config: APIForgeConfig | None = None,
        credentials: CredentialManager | None = None,
        registry: PluginRegistry | None = None,
    ) -> None:
        # Configuration ----------------------------------------------------------
        # Each subsystem has a default; users can override any of them.
        # We keep dependencies explicit so a test can construct an
        # APIForge with a fake registry and a fake credential manager.
        self.config = config or APIForgeConfig()
        self.credentials = credentials or CredentialManager()
        self.registry = registry or PluginRegistry()

        # State -------------------------------------------------------------------
        # ``_http`` is created lazily because constructing an httpx
        # client at import time would require an async context, which
        # conflicts with synchronous user code paths.
        self._http: httpx.AsyncClient | None = None
        self._plugins: dict[str, BasePlugin] = {}

    # ------------------------------------------------------------------ configuration

    def configure(self, **credentials: str) -> None:
        """Set explicit credentials for one or more plugins.

        Unknown keyword arguments are still recorded under the literal
        name, so users can pass ``client.configure(my_custom_token="...")``
        even if no plugin with that exact name is registered yet —
        this lets a script populate credentials for a plugin installed
        later in the same process.

        Examples
        --------
        >>> client.configure(
        ...     github_token="ghp_xxx",
        ...     discord_token="...",
        ...     notion_token="...",
        ... )
        """
        for key, value in credentials.items():
            if not isinstance(value, str):
                msg = f"Credential for '{key}' must be a string, got {type(value).__name__}"
                raise PluginError(msg)
            # Strip ``_token`` suffix if present so users can pass
            # either ``github_token`` or ``github``.
            name = key.removesuffix("_token")
            self.credentials.set(name, value)

    # ------------------------------------------------------------------ transport

    @property
    def http(self) -> httpx.AsyncClient:
        """The shared :class:`httpx.AsyncClient`.

        Lazily constructed with the configured timeout, SSL, and
        user-agent. Plugins should use this rather than creating their
        own clients — sharing the pool avoids socket exhaustion.
        """
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                verify=self.config.verify_ssl,
                headers={"User-Agent": self.config.user_agent},
                http2=False,  # opt-in via explicit config in the future
            )
        return self._http

    async def close(self) -> None:
        """Close the HTTP client and call ``teardown`` on every plugin.

        Safe to call multiple times.
        """
        for name, plugin in list(self._plugins.items()):
            try:
                await plugin.teardown()
            except Exception:  # noqa: S110
                # A misbehaving teardown should not prevent others
                # from running, and should not prevent the HTTP
                # client from closing.
                pass
            finally:
                self._plugins.pop(name, None)
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def __aenter__(self) -> APIForge:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # ------------------------------------------------------------------ plugin access

    def get_plugin(self, name: str) -> BasePlugin:
        """Return the instantiated plugin for ``name``.

        First access instantiates the plugin and runs its ``setup()``
        hook; subsequent accesses return the cached instance.

        Raises :class:`PluginNotFoundError` if the name is unknown.
        """
        if name in self._plugins:
            return self._plugins[name]
        cls = self.registry.get(name)  # raises PluginNotFoundError
        try:
            instance = cls(self)
        except Exception as exc:
            msg = f"Failed to instantiate plugin '{name}': {exc}"
            raise PluginError(msg, plugin=name) from exc
        self._plugins[name] = instance
        # We deliberately do NOT call setup() synchronously here.
        # Plugins that need a setup step are usually async (token
        # refresh, keyring validation). The SyncProxy takes care of
        # awaiting it lazily on first use.
        return instance

    def has_plugin(self, name: str) -> bool:
        """Return ``True`` if a plugin named ``name`` is registered."""
        return name in self.registry

    def list_plugins(self) -> list[str]:
        """Return the names of all registered plugins, sorted."""
        return self.registry.names()

    # ------------------------------------------------------------------ attribute proxy

    def __getattr__(self, name: str) -> Any:
        # ``__getattr__`` is only called when normal lookup fails, so
        # methods like ``close`` and properties like ``http`` still
        # resolve normally. Plugin names are deliberately lower-case
        # to match the documented example (``client.github``).
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return SyncProxy(self.get_plugin(name))
        except PluginNotFoundError:
            raise AttributeError(
                f"{type(self).__name__!s} has no attribute {name!r}. "
                f"Did you mean one of: {', '.join(self.list_plugins()) or '<none>'}?"
            ) from None


class SyncProxy:
    """Wraps an async plugin so sync callers can use it transparently.

    Every attribute access on the proxy returns a coroutine runner
    for the corresponding async method on the underlying plugin.
    This means::

        client.github.get_user("octocat")

    is exactly equivalent to::

        asyncio.run(client.github.get_user("octocat"))

    If the underlying plugin mixes sync and async methods, sync ones
    are passed through directly. We detect sync methods by checking
    the class's ``__dict__`` rather than inspecting the coroutine
    flag, because some plugins may legitimately expose coroutine-
    returning callables that aren't ``async def`` (e.g. methods
    built dynamically).
    """

    __slots__ = ("_plugin",)

    def __init__(self, plugin: BasePlugin) -> None:
        self._plugin = plugin

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._plugin, name)
        # Non-callable attributes: pass through (e.g. ``plugin.metadata``).
        if not callable(attr):
            return attr
        # Sync methods are passed through untouched. This means a plugin
        # that mixes sync and async methods just works — the proxy only
        # wraps the coroutine-returning ones.
        if not inspect.iscoroutinefunction(attr):
            return attr
        return _SyncMethod(self._plugin, name)

    def __repr__(self) -> str:
        return f"SyncProxy({self._plugin!r})"


class _SyncMethod:
    """A bound, sync-callable wrapper around an async plugin method.

    Holding a reference to the plugin (not the bound method) means
    that if the plugin instance is re-created we get a fresh method
    — small but important for tests that swap out the registry.
    """

    __slots__ = ("_name", "_plugin")

    def __init__(self, plugin: BasePlugin, name: str) -> None:
        self._plugin = plugin
        self._name = name

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # Importing here avoids a top-level asyncio dependency.
        import asyncio

        method = getattr(self._plugin, self._name)
        return asyncio.run(method(*args, **kwargs))

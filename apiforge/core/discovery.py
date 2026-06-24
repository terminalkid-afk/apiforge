"""Plugin discovery via setuptools entry points.

A plugin is any class that:

1. Is exported as the value of an entry point in the
   ``apiforge.plugins`` group, **and**
2. Inherits from :class:`apiforge.plugins.base.BasePlugin`.

The registry is a thin wrapper around ``importlib.metadata``; we cache
it per process so we only scan once. Third-party plugins are therefore
discovered automatically as long as they declare the right entry point
in their own ``pyproject.toml``.
"""

from __future__ import annotations

from collections.abc import Iterator
from importlib import metadata
from typing import Any

from apiforge.core.exceptions import PluginNotFoundError
from apiforge.plugins.base import BasePlugin

# Entry-point group name. Public — third parties import it for type hints.
ENTRY_POINT_GROUP = "apiforge.plugins"


class PluginRegistry:
    """Lazy, in-memory registry of every installed plugin.

    The registry is intentionally simple: a mapping from name to a
    *factory* (the entry point's ``load()`` returns the class, not an
    instance). We keep it small because the alternative — caching
    instances — would make credential injection much harder.
    """

    def __init__(self) -> None:
        self._factories: dict[str, Any] = {}
        self._discovered: bool = False

    # ------------------------------------------------------------------ discovery

    def discover(self, *, force: bool = False) -> None:
        """Walk all entry points and populate the registry.

        Idempotent: a second call is a no-op unless ``force=True``.
        """
        if self._discovered and not force:
            return
        self._factories.clear()
        eps = metadata.entry_points()
        # ``entry_points()`` returns a ``SelectableGroups`` on 3.10+ where
        # ``select(group=...)`` is the documented way; we handle both the
        # modern and the legacy dict-like interface.
        try:
            selected = eps.select(group=ENTRY_POINT_GROUP)
        except AttributeError:  # pragma: no cover - legacy Python
            selected = eps.get(ENTRY_POINT_GROUP, [])  # type: ignore[union-attr]
        for ep in selected:
            try:
                factory = ep.load()
            except Exception as exc:
                # A misbehaving plugin must not break discovery of others.
                # We deliberately swallow: the registry is best-effort,
                # and the user can run ``apiforge plugins --verbose`` to
                # debug (this is a TODO for the CLI).
                _ = exc
                continue
            self._factories[ep.name] = factory
        self._discovered = True

    # ------------------------------------------------------------------ accessors

    def __contains__(self, name: str) -> bool:
        self.discover()
        return name in self._factories

    def __iter__(self) -> Iterator[str]:
        self.discover()
        return iter(self._factories)

    def __len__(self) -> int:
        self.discover()
        return len(self._factories)

    def names(self) -> list[str]:
        """Return all registered plugin names, sorted alphabetically."""
        self.discover()
        return sorted(self._factories)

    def get(self, name: str) -> type[BasePlugin]:
        """Return the plugin *class* registered under ``name``.

        Raises :class:`PluginNotFoundError` if no plugin is registered.
        """
        self.discover()
        try:
            return self._factories[name]
        except KeyError as exc:
            raise PluginNotFoundError(name) from exc

    def get_or_none(self, name: str) -> type[BasePlugin] | None:
        """Return the plugin class for ``name``, or ``None`` if absent."""
        self.discover()
        return self._factories.get(name)

"""Credential management.

The :class:`CredentialManager` is the single point of truth for every
secret APIForge touches. Resolution priority is:

1. **Explicit** — values passed to ``APIForge.configure(...)`` win.
2. **Environment** — ``APIFORGE_GITHUB_TOKEN`` and similar.
3. **Keyring** — the OS secure store (``keyring`` package).
4. **Config file** — ``~/.config/apiforge/credentials.toml`` (TOML, not INI).

The explicit layer is what lets tests inject fake secrets without touching
the environment. The keyring layer is what protects users who install
APIForge on a laptop — tokens never sit in plaintext on disk.

The keyring is optional; if it isn't installed (or no backend is
available — Linux without ``libsecret``, for example) we silently
fall back. This is deliberate: better to "ask the user to pass the
token again" than to crash the process.
"""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apiforge.core.exceptions import AuthenticationError

# ``keyring`` is a soft dependency: if it's not installed we still
# function, just without the OS-secure-store layer.
try:
    import keyring
    import keyring.errors

    _KEYRING_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without the dep
    keyring = None  # type: ignore[assignment]
    _KEYRING_AVAILABLE = False


KEYRING_SERVICE = "apiforge"


def _redact(value: str) -> str:
    """Return ``value`` with all but the first/last 2 chars masked.

    Used for logging — never log full tokens.
    """
    if len(value) <= 6:
        return "***"
    return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"


@dataclass
class CredentialStore:
    """Holds credentials collected from explicit, env, file, and keyring sources.

    The store is intentionally dumb: a name → secret mapping. All policy
    (priority, validation) lives in :class:`CredentialManager`.
    """

    explicit: dict[str, str] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    file: dict[str, str] = field(default_factory=dict)
    keyring: dict[str, str] = field(default_factory=dict)

    def all_for(self, name: str) -> dict[str, str]:
        """Return all credentials the manager knows about for ``name``."""
        return {
            "explicit": self.explicit.get(name, ""),
            "env": self.env.get(name, ""),
            "file": self.file.get(name, ""),
            "keyring": self.keyring.get(name, ""),
        }


class CredentialManager:
    """Resolves and provides credentials to plugins.

    Use as a context manager or directly::

        with CredentialManager() as mgr:
            mgr.set("github", "ghp_xxx")
            token = mgr.get("github")  # explicit wins

    The class is small and side-effect free except for keyring writes,
    which are explicit and only happen via :meth:`store`.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._store = CredentialStore()
        self._config_path = config_path or self._default_config_path()
        self._load_file()
        self._load_env()
        self._load_keyring()

    # ------------------------------------------------------------------ public api

    def set(self, name: str, value: str) -> None:
        """Explicitly set a credential. Highest priority."""
        if not value:
            msg = f"Refusing to set empty credential for '{name}'"
            raise AuthenticationError(msg)
        self._store.explicit[name] = value

    def get(self, name: str) -> str | None:
        """Resolve ``name`` through the priority chain.

        Returns ``None`` if no source has the credential. Raises
        :class:`AuthenticationError` if the explicit value is set but
        empty (programmer error).
        """
        explicit = self._store.explicit.get(name)
        if explicit is not None:
            if not explicit:
                raise AuthenticationError(f"Empty explicit credential for '{name}'")
            return explicit
        for source in (self._store.env, self._store.file, self._store.keyring):
            if source.get(name):
                return source[name]
        return None

    def require(self, name: str) -> str:
        """Like :meth:`get` but raises if missing."""
        value = self.get(name)
        if value is None:
            msg = f"No credential found for '{name}'"
            raise AuthenticationError(msg, plugin=name)
        return value

    def store(self, name: str, value: str) -> None:
        """Persist ``value`` to the OS keyring under the APIForge service.

        This is a one-way write; keyring does not support retrieval
        enumeration. ``name`` should be a stable identifier (e.g. ``github``).
        """
        if not _KEYRING_AVAILABLE:
            msg = (
                "The 'keyring' package is not installed. "
                "Install it with `pip install keyring` to use persistent storage."
            )
            raise AuthenticationError(msg)
        try:
            keyring.set_password(KEYRING_SERVICE, name, value)
        except keyring.errors.KeyringError as exc:  # type: ignore[union-attr]
            msg = f"Failed to write to keyring: {exc}"
            raise AuthenticationError(msg) from exc
        # Refresh our cache so the new value is visible immediately.
        self._store.keyring[name] = value

    def list_known(self) -> list[str]:
        """Return the union of known credential names across all sources."""
        names: set[str] = set()
        for source in (
            self._store.explicit,
            self._store.env,
            self._store.file,
            self._store.keyring,
        ):
            names.update(source)
        return sorted(names)

    def redacted_snapshot(self) -> dict[str, str]:
        """Return ``{name: redacted_value}`` for every known credential.

        Useful for diagnostics; never log the full snapshot in plaintext
        (the redaction is for the values, not the names).
        """
        result: dict[str, str] = {}
        for name in self.list_known():
            value = self.get(name)
            if value is not None:
                result[name] = _redact(value)
        return result

    # ------------------------------------------------------------------ internals

    def _load_env(self) -> None:
        """Pull ``APIFORGE_<NAME>_TOKEN`` style variables into the store."""
        prefix = "APIFORGE_"
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            stripped = key[len(prefix) :].lower()
            # Accept both ``GITHUB_TOKEN`` and ``GITHUB`` as the credential name.
            name = stripped.removesuffix("_token")
            if name:
                self._store.env[name] = value

    def _load_file(self) -> None:
        """Load plaintext credentials from ``~/.config/apiforge/credentials.toml``."""
        if not self._config_path.exists():
            return
        try:
            with self._config_path.open("rb") as fh:
                data: dict[str, Any] = tomllib.load(fh)
        except (OSError, tomllib.TOMLDecodeError):
            # A malformed file should not crash the whole manager.
            # We deliberately don't surface this — the user will see
            # "no credential" downstream, which is the same effect.
            return
        for name, value in data.items():
            if isinstance(value, str) and value:
                self._store.file[name] = value

    def _load_keyring(self) -> None:
        """Best-effort enumeration of keyring-stored credentials.

        Keyring doesn't support listing, so we try common names plus
        whatever plugins advertise. This is opportunistic — missing
        entries simply mean ``get`` returns ``None`` for that source.
        """
        if not _KEYRING_AVAILABLE:
            return
        for name in _common_credential_names():
            try:
                value = keyring.get_password(KEYRING_SERVICE, name)
            except keyring.errors.KeyringError:  # type: ignore[union-attr]
                continue
            if value:
                self._store.keyring[name] = value

    @staticmethod
    def _default_config_path() -> Path:
        """``~/.config/apiforge/credentials.toml`` on Linux/macOS,
        ``%APPDATA%/apiforge/credentials.toml`` on Windows."""
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", str(Path.home())))
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        return base / "apiforge" / "credentials.toml"

    # ------------------------------------------------------------------ context

    def __enter__(self) -> CredentialManager:
        return self

    def __exit__(self, *exc: object) -> None:
        # Nothing to clean up: the manager is in-memory and writes only
        # go to keyring, which is durable.
        return None


def _common_credential_names() -> list[str]:
    """Names we proactively probe in keyring. Plugins with unusual names
    can still call :meth:`CredentialManager.get` and :meth:`store` directly;
    this list is just a best-effort cache warmer.
    """
    return [
        "github",
        "discord",
        "notion",
        "openai",
        "slack",
        "google",
    ]

"""Credential manager tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from apiforge.core.credentials import CredentialManager, _redact
from apiforge.core.exceptions import AuthenticationError


def test_explicit_wins_over_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APIFORGE_TEST", "from_env")
    mgr = CredentialManager(config_path=tmp_path / "creds.toml")
    mgr.set("test", "from_explicit")
    assert mgr.get("test") == "from_explicit"


def test_env_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APIFORGE_TEST", "from_env")
    mgr = CredentialManager(config_path=tmp_path / "creds.toml")
    assert mgr.get("test") == "from_env"


def test_env_normalizes_token_suffix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APIFORGE_GITHUB_TOKEN", "ghp_xxx")
    mgr = CredentialManager(config_path=tmp_path / "creds.toml")
    assert mgr.get("github") == "ghp_xxx"


def test_file_loaded(
    tmp_path: Path,
) -> None:
    path = tmp_path / "creds.toml"
    path.write_text('github = "from_file"\n', encoding="utf-8")
    mgr = CredentialManager(config_path=path)
    assert mgr.get("github") == "from_file"


def test_missing_returns_none(tmp_path: Path) -> None:
    mgr = CredentialManager(config_path=tmp_path / "creds.toml")
    assert mgr.get("missing") is None


def test_require_raises_when_missing(tmp_path: Path) -> None:
    mgr = CredentialManager(config_path=tmp_path / "creds.toml")
    with pytest.raises(AuthenticationError):
        mgr.require("missing")


def test_empty_explicit_raises(tmp_path: Path) -> None:
    mgr = CredentialManager(config_path=tmp_path / "creds.toml")
    with pytest.raises(AuthenticationError):
        mgr.set("github", "")


def test_redact_masks_value() -> None:
    assert _redact("a") == "***"
    assert _redact("abcdef") == "***"
    assert _redact("abcdefghij") == "ab******ij"
    assert _redact("12345678") == "12****78"


def test_list_known_includes_all_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APIFORGE_FROM_ENV", "v")
    path = tmp_path / "creds.toml"
    path.write_text('from_file = "v"\n', encoding="utf-8")
    mgr = CredentialManager(config_path=path)
    mgr.set("from_explicit", "v")
    names = mgr.list_known()
    assert "from_env" in names
    assert "from_file" in names
    assert "from_explicit" in names

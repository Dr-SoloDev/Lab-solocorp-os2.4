"""Provider settings: explicit choice, credential kept out of the tracked file.

Covers PRD §9 (credentials stay in local configuration, outside task artifacts)
and design note §4 D5 (one provider, no silent fallback).
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from solocorp_app.provider import (
    DEFAULT_API_KEY_REF,
    ProviderError,
    ProviderStore,
    mask_credential,
)


@pytest.fixture
def store(tmp_path: Path) -> ProviderStore:
    return ProviderStore(
        config_path=tmp_path / "config" / "provider.json",
        credentials_path=tmp_path / "config" / "provider.credentials.json",
        env={},
    )


def test_first_run_is_unconfigured(store):
    status = store.status()

    assert status["state"] == "unconfigured"
    assert status["provider"] is None
    assert status["model"] is None
    assert status["credential_present"] is False
    assert status["errors"] == []


def test_save_writes_choice_without_the_secret(store):
    settings = store.save(
        provider="OpenCode",
        model="deepseek-v4.1-flash-free",
        base_url="https://api.example.test/v1",
        api_key="sk-super-secret-value",
    )

    assert settings.provider == "opencode"  # normalised, not trusted verbatim
    config_text = store.config_path.read_text(encoding="utf-8")
    config = json.loads(config_text)
    assert config["provider"] == "opencode"
    assert config["model"] == "deepseek-v4.1-flash-free"
    assert config["base_url"] == "https://api.example.test/v1"
    assert config["api_key_ref"] == DEFAULT_API_KEY_REF
    assert "sk-super-secret-value" not in config_text

    credentials = json.loads(store.credentials_path.read_text(encoding="utf-8"))
    assert credentials[DEFAULT_API_KEY_REF] == "sk-super-secret-value"

    status = store.status()
    assert status["state"] == "configured"
    assert status["credential_source"] == "file"
    assert status["credential_hint"] == "…alue"
    assert "sk-super-secret-value" not in json.dumps(status)


def test_credentials_file_is_owner_only(store):
    store.save(provider="openai", model="gpt-test", api_key="sk-secret-abcdef")

    mode = stat.S_IMODE(store.credentials_path.stat().st_mode)
    assert mode == 0o600


def test_environment_variable_wins_over_the_file(tmp_path: Path):
    credentials_path = tmp_path / "config" / "provider.credentials.json"
    file_store = ProviderStore(
        config_path=tmp_path / "config" / "provider.json",
        credentials_path=credentials_path,
        env={},
    )
    file_store.save(provider="openai", model="gpt-test", api_key="from-the-file")

    env_store = ProviderStore(
        config_path=tmp_path / "config" / "provider.json",
        credentials_path=credentials_path,
        env={DEFAULT_API_KEY_REF: "from-the-environment"},
    )

    assert env_store.credential() == "from-the-environment"
    assert env_store.status()["credential_source"] == "env"


def test_model_without_credential_stays_unconfigured(store, tmp_path: Path):
    # A hand-written config (no credential anywhere) must not claim readiness.
    store.config_path.parent.mkdir(parents=True, exist_ok=True)
    store.config_path.write_text(
        json.dumps({"provider": "openai", "model": "gpt-test"}), encoding="utf-8"
    )

    status = store.status()
    assert status["state"] == "unconfigured"
    assert status["provider"] == "openai"
    assert status["credential_present"] is False


def test_corrupt_config_reports_failed_not_a_crash(store):
    store.config_path.parent.mkdir(parents=True, exist_ok=True)
    store.config_path.write_text("{not json", encoding="utf-8")

    status = store.status()
    assert status["state"] == "failed"
    assert status["provider"] is None
    assert any("not valid JSON" in error for error in status["errors"])


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"provider": "", "model": "m"}, "provider must be"),
        ({"provider": "Upper Case", "model": "m"}, "provider must be"),
        ({"provider": "openai", "model": "   "}, "model is required"),
        (
            {"provider": "openai", "model": "m" * 121},
            "at most 120 characters",
        ),
        (
            {"provider": "openai", "model": "m", "base_url": "ftp://x.test"},
            "start with http://",
        ),
        (
            {"provider": "openai", "model": "m", "api_key": "ab"},
            "at least 4 characters",
        ),
        (
            {"provider": "openai", "model": "m", "api_key_ref": "lower-case"},
            "environment variable name",
        ),
    ],
)
def test_save_rejects_invalid_input_without_writing(store, kwargs, message):
    with pytest.raises(ProviderError, match=message):
        store.save(**kwargs)

    assert store.config_path.exists() is False
    assert store.credentials_path.exists() is False


def test_clear_credential_removes_only_the_slot(store):
    store.save(provider="openai", model="gpt-test", api_key="sk-secret-abcdef")

    assert store.clear_credential() is True
    assert store.status()["state"] == "unconfigured"
    assert store.clear_credential() is False


def test_replacing_the_credential_keeps_the_choice(store):
    store.save(provider="openai", model="gpt-test", api_key="first-secret-key")
    store.save(provider="openai", model="gpt-test", api_key="second-secret-key")

    assert store.credential() == "second-secret-key"
    assert store.status()["credential_hint"] == "…-key"


@pytest.mark.parametrize(
    ("secret", "expected"),
    [(None, None), ("abcdefgh", "…gh"), ("sk-1234567890abcd", "…abcd")],
)
def test_mask_credential_never_returns_the_whole_value(secret, expected):
    masked = mask_credential(secret)
    assert masked == expected
    if secret:
        assert secret not in masked

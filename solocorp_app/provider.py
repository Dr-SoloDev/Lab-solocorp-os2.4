"""Explicit provider/model configuration for the SoloCorp App.

Contract (design note §4 D5, PRD §9):

* ``config/provider.json`` holds the **choice** — provider, model, optional
  base URL and the *name* of the credential slot (``api_key_ref``). It carries
  no secret, so it is safe to track in git.
* ``config/provider.credentials.json`` holds the **credential**. It is
  git-ignored and written with mode ``0600``. An environment variable with the
  same name as ``api_key_ref`` wins over the file, so an operator can inject a
  secret without touching disk.
* There is exactly one configured provider and model. Nothing here falls back
  to a different model or vendor: a missing credential is reported as
  ``unconfigured`` and a broken config file as ``failed`` (design §5.3), never
  silently replaced.

The credential is never returned raw by this module — only ``credential_hint``
(the last four characters) for display.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_CONFIG_PATH = ROOT / "config" / "provider.json"
DEFAULT_CREDENTIALS_PATH = ROOT / "config" / "provider.credentials.json"

# Name of the credential slot used when the caller does not name one. The value
# is an environment variable name, not a key: the same slot can be satisfied by
# the env var or by the local credentials file.
DEFAULT_API_KEY_REF = "SOLOCORP_PROVIDER_API_KEY"

CONFIG_SCHEMA_VERSION = 1

PROVIDER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,31}$")
API_KEY_REF_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")

MAX_MODEL_LENGTH = 120
MAX_BASE_URL_LENGTH = 300
MIN_API_KEY_LENGTH = 4

# Provider states, one vocabulary shared with the UI and the registry status
# model (design §5.3). No fourth word is allowed.
STATE_CONFIGURED = "configured"
STATE_UNCONFIGURED = "unconfigured"
STATE_FAILED = "failed"


class ProviderError(ValueError):
    """A user-facing provider configuration problem (shown in the UI)."""


@dataclass(frozen=True)
class ProviderSettings:
    """The operator's explicit provider choice (never contains a secret)."""

    provider: str
    model: str
    api_key_ref: str = DEFAULT_API_KEY_REF
    base_url: str | None = None
    updated_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "api_key_ref": self.api_key_ref,
            "base_url": self.base_url,
            "updated_at": self.updated_at,
        }


def mask_credential(secret: str | None) -> str | None:
    """Return a display-only hint: the last four characters, never the key."""

    if not secret:
        return None
    if len(secret) <= 8:
        return "…" + secret[-2:]
    return "…" + secret[-4:]


class ProviderStore:
    """Read/write the provider choice and its credential slot."""

    def __init__(
        self,
        config_path: Path | None = None,
        credentials_path: Path | None = None,
        *,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.credentials_path = (
            Path(credentials_path) if credentials_path else DEFAULT_CREDENTIALS_PATH
        )
        self._env = os.environ if env is None else env

    # ------------------------------------------------------------------ read

    def read(self) -> tuple[ProviderSettings | None, list[str]]:
        """Read the provider config; return ``(settings, errors)``.

        Never raises: a missing file is ``(None, [])`` (first run) and an
        unreadable or invalid file is ``(None, [reason])`` so ``status()`` can
        report ``failed`` instead of blowing up a page render.
        """

        if not self.config_path.exists():
            return None, []

        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                document = json.load(handle)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return None, [f"{self.config_path.name} is not valid JSON: {exc}"]
        except OSError as exc:
            return None, [f"{self.config_path.name} cannot be read: {exc}"]

        if not isinstance(document, dict):
            return None, [f"{self.config_path.name} root must be an object"]

        provider = document.get("provider")
        model = document.get("model")
        if not isinstance(provider, str) or not provider.strip():
            return None, [f"{self.config_path.name}: provider must be a string"]
        if not isinstance(model, str) or not model.strip():
            return None, [f"{self.config_path.name}: model must be a string"]

        api_key_ref = document.get("api_key_ref")
        if not isinstance(api_key_ref, str) or not api_key_ref.strip():
            api_key_ref = DEFAULT_API_KEY_REF

        base_url = document.get("base_url")
        if base_url is not None and not isinstance(base_url, str):
            return None, [f"{self.config_path.name}: base_url must be a string"]

        updated_at = document.get("updated_at")
        if not isinstance(updated_at, str):
            updated_at = None

        return (
            ProviderSettings(
                provider=provider.strip(),
                model=model.strip(),
                api_key_ref=api_key_ref.strip(),
                base_url=base_url.strip() if base_url else None,
                updated_at=updated_at,
            ),
            [],
        )

    def load(self) -> ProviderSettings | None:
        """Strict read used by callers that need the choice or nothing."""

        settings, errors = self.read()
        if errors:
            raise ProviderError("; ".join(errors))
        return settings

    # ------------------------------------------------------------- credential

    def credential(self, settings: ProviderSettings | None = None) -> str | None:
        """Resolve the credential: environment first, then the local file."""

        settings = settings if settings is not None else self.load()
        if settings is None:
            return None
        env_value = self._env.get(settings.api_key_ref)
        if isinstance(env_value, str) and env_value.strip():
            return env_value.strip()

        document = self._read_credentials()
        if document is None:
            return None
        value = document.get(settings.api_key_ref)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def credential_source(self, settings: ProviderSettings | None = None) -> str | None:
        """Where the credential came from: ``env``, ``file`` or ``None``."""

        settings = settings if settings is not None else self.load()
        if settings is None:
            return None
        env_value = self._env.get(settings.api_key_ref)
        if isinstance(env_value, str) and env_value.strip():
            return "env"
        document = self._read_credentials() or {}
        value = document.get(settings.api_key_ref)
        if isinstance(value, str) and value.strip():
            return "file"
        return None

    def clear_credential(self, api_key_ref: str | None = None) -> bool:
        """Remove the stored credential; return True when something was removed."""

        document = self._read_credentials()
        if not document:
            return False
        ref = api_key_ref or DEFAULT_API_KEY_REF
        if ref not in document:
            return False
        del document[ref]
        self._write_private_json(self.credentials_path, document)
        return True

    def _read_credentials(self) -> dict[str, Any] | None:
        if not self.credentials_path.exists():
            return None
        try:
            with open(self.credentials_path, "r", encoding="utf-8") as handle:
                document = json.load(handle)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            return None
        if not isinstance(document, dict):
            return None
        return {key: value for key, value in document.items() if isinstance(key, str)}

    # ----------------------------------------------------------------- write

    def save(
        self,
        *,
        provider: str,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        api_key_ref: str | None = None,
    ) -> ProviderSettings:
        """Validate and persist the choice; the credential only when supplied.

        Validation happens before either file is touched, so a rejected form
        never leaves a half-written configuration behind.
        """

        clean_provider = (provider or "").strip().lower()
        if not PROVIDER_PATTERN.fullmatch(clean_provider):
            raise ProviderError(
                "provider must be 1-32 characters of a-z, 0-9, '.', '_' or '-'"
            )

        clean_model = (model or "").strip()
        if not clean_model:
            raise ProviderError("model is required")
        if len(clean_model) > MAX_MODEL_LENGTH:
            raise ProviderError(f"model must be at most {MAX_MODEL_LENGTH} characters")
        if any(character in clean_model for character in "\r\n\t"):
            raise ProviderError("model must not contain whitespace control characters")

        clean_base_url = (base_url or "").strip() or None
        if clean_base_url is not None:
            if len(clean_base_url) > MAX_BASE_URL_LENGTH:
                raise ProviderError(
                    f"base_url must be at most {MAX_BASE_URL_LENGTH} characters"
                )
            if not clean_base_url.startswith(("http://", "https://")):
                raise ProviderError("base_url must start with http:// or https://")
            if any(character.isspace() for character in clean_base_url):
                raise ProviderError("base_url must not contain whitespace")

        clean_ref = (api_key_ref or DEFAULT_API_KEY_REF).strip()
        if not API_KEY_REF_PATTERN.fullmatch(clean_ref):
            raise ProviderError(
                "api_key_ref must look like an environment variable name "
                "(A-Z, 0-9, underscore)"
            )

        clean_key = (api_key or "").strip() or None
        if clean_key is not None and len(clean_key) < MIN_API_KEY_LENGTH:
            raise ProviderError(
                f"api_key must be at least {MIN_API_KEY_LENGTH} characters"
            )

        settings = ProviderSettings(
            provider=clean_provider,
            model=clean_model,
            api_key_ref=clean_ref,
            base_url=clean_base_url,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Credential first: a stray git-ignored key file is harmless, while a
        # config claiming a credential that was never written is a lie.
        if clean_key is not None:
            document = self._read_credentials() or {}
            document[clean_ref] = clean_key
            self._write_private_json(self.credentials_path, document)

        self._write_json(
            self.config_path,
            {"schema_version": CONFIG_SCHEMA_VERSION, **settings.as_dict()},
        )
        return settings

    # ---------------------------------------------------------------- status

    def status(self) -> dict[str, Any]:
        """Return the provider state, masked credentials and file locations."""

        settings, errors = self.read()
        source = self.credential_source(settings) if settings else None
        credential = self.credential(settings) if settings else None
        present = credential is not None

        if errors:
            state = STATE_FAILED
        elif settings is None or not present:
            state = STATE_UNCONFIGURED
        else:
            state = STATE_CONFIGURED

        return {
            "state": state,
            "provider": settings.provider if settings else None,
            "model": settings.model if settings else None,
            "base_url": settings.base_url if settings else None,
            "api_key_ref": (settings.api_key_ref if settings else DEFAULT_API_KEY_REF),
            "credential_present": present,
            "credential_source": source,
            "credential_hint": mask_credential(credential),
            "config_path": str(self.config_path),
            "credentials_path": str(self.credentials_path),
            "updated_at": settings.updated_at if settings else None,
            "errors": errors,
        }

    # ------------------------------------------------------------------- i/o

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        _atomic_write(path, data, mode=0o644)

    @staticmethod
    def _write_private_json(path: Path, data: dict[str, Any]) -> None:
        _atomic_write(path, data, mode=0o600)


def _atomic_write(path: Path, data: dict[str, Any], *, mode: int) -> None:
    """Write JSON atomically with an explicit mode (0600 for credentials)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        os.chmod(temp_path, mode)
        with handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except BaseException:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise

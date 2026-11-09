"""Schema and validation for module registry config and state files.

Locks the shape of:

* ``config/module-registry.json`` — human intent: enabled/disabled, transport,
  entry point, description, and the declared module manifest (name, version,
  capabilities, dependencies, permissions, entry_repo). Changes only when a
  person changes it.
* ``central_bus/module-registry.state.json`` — runtime observation
  (connected/connecting/error, last_checked, response_time_ms, last_error).
  Written on every heartbeat.

Manifest fields are declarative metadata, never enforcement: ``permissions``
names the scopes a module's own tools use, and nothing here gates a
connect/call on it (FR-07).

Schema v2 rules (CMD-006 §2.4): an absent ``_meta.schema_version`` means v1 and
is accepted; anything below ``SCHEMA_VERSION`` is accepted (so an upgrade never
invalidates existing installs); anything above it raises
``RegistryDowngradeError`` before field validation runs.

No external dependencies: pure Python validation so the registry never needs
an extra library just to read its own config. A corrupted or hand-edited file
is rejected loudly rather than silently misinterpreted.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .auth import SCOPE_LEVELS

# --- Schema constants -----------------------------------------------------

# Statuses that describe intent and therefore live in the tracked config.
PERSISTENT_STATUSES = frozenset({"enabled", "disabled"})

# Statuses that describe an observation and therefore live in the state file.
RUNTIME_STATUSES = frozenset({"connected", "connecting", "error"})

VALID_STATUSES = PERSISTENT_STATUSES | RUNTIME_STATUSES

# Transport values allowed in config.
VALID_TRANSPORTS = frozenset({"stdio"})

# Permission levels are the scopes a module's own tools declare — provider-side
# metadata, not an access gate the app enforces (CMD-006 §1.4). The vocabulary
# is imported from ``auth`` so there is never a second word list for scopes
# (DESIGN §5.3). ``SCOPE_LEVELS`` also gives the canonical write order.
VALID_PERMISSION_LEVELS: frozenset[str] = frozenset(SCOPE_LEVELS)

# MCP primitive kinds a module may advertise.
VALID_CAPABILITIES = frozenset({"tools", "resources", "prompts"})

# Dependencies that are shared infrastructure rather than registry modules.
INFRA_DEPENDENCIES = frozenset({"busd"})

# Entry-point field required for each transport. ``command`` is no longer
# unconditionally required: it is required *for stdio* and forbidden for a
# transport that does not take a command, so adding ``http`` later is an enum
# value plus an entry field, not a breaking change (CMD-006 §3.2).
TRANSPORT_ENTRY_FIELDS: dict[str, frozenset[str]] = {"stdio": frozenset({"command"})}
TRANSPORT_ONLY_FIELDS = frozenset().union(*TRANSPORT_ENTRY_FIELDS.values())

# Field names per file layer.
CONFIG_REQUIRED_FIELDS = frozenset({"status", "transport"})

# Manifest fields: declarative metadata about the module. Optional by design —
# a config written before C2 (schema v1) stays readable (CMD-006 §3.1).
CONFIG_MANIFEST_FIELDS = frozenset(
    {"name", "version", "capabilities", "dependencies", "permissions", "entry_repo"}
)
CONFIG_LOCAL_FIELDS = frozenset({"description", "updated_at"})
CONFIG_OPTIONAL_FIELDS = CONFIG_LOCAL_FIELDS | CONFIG_MANIFEST_FIELDS
CONFIG_ALL_FIELDS = (
    CONFIG_REQUIRED_FIELDS | CONFIG_OPTIONAL_FIELDS | TRANSPORT_ONLY_FIELDS
)

STATE_REQUIRED_FIELDS = frozenset({"status", "last_checked"})
STATE_OPTIONAL_FIELDS = frozenset({"response_time_ms", "last_error"})
STATE_ALL_FIELDS = STATE_REQUIRED_FIELDS | STATE_OPTIONAL_FIELDS

META_FIELDS = frozenset({"last_updated", "total_modules", "schema_version"})

# Bump when the on-disk shape changes in a way old readers cannot accept:
# *if a file this code writes would be rejected by the previous code*, bump.
# Adding an optional field counts, because an old reader rejects unknown
# fields. Reading an older file never needs migration code.
#
# v2 (C2): the six manifest fields + ``permissions`` are written to config.
SCHEMA_VERSION = 2

# A legacy file with no ``_meta.schema_version`` is this old.
LEGACY_SCHEMA_VERSION = 1

# ``version`` is a declared module version, not a runtime observation.
VERSION_PATTERN = re.compile(
    r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.+-]{1,32})?$"
)

# --- Errors ---------------------------------------------------------------


class RegistrySchemaError(ValueError):
    """Raised when a registry file violates its schema."""


class RegistryDowngradeError(RegistrySchemaError):
    """Raised when a config was written by a newer schema than this build supports."""


# --- Helpers --------------------------------------------------------------


def _is_iso_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def _non_empty_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(isinstance(item, str) and item for item in value)
    )


def _as_string_list(
    value: Any, prefix: str, field: str
) -> tuple[list[str] | None, list[str]]:
    """Return ``(items, errors)``; ``items`` is ``None`` for a non-string-list."""

    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None, [f"{prefix}: {field} must be a list of strings"]
    return list(value), []


def _duplicates(items: list[str]) -> list[str]:
    """Return the repeated values, sorted, each named once."""

    seen: set[str] = set()
    repeated: list[str] = []
    for item in items:
        if item in seen and item not in repeated:
            repeated.append(item)
        seen.add(item)
    return sorted(repeated)


def _validate_name(value: Any, prefix: str) -> list[str]:
    if not isinstance(value, str):
        return [f"{prefix}: name must be a string"]
    errors: list[str] = []
    if not 1 <= len(value) <= 64:
        errors.append(f"{prefix}: name must be 1-64 characters")
    if value != value.strip():
        errors.append(f"{prefix}: name must not start or end with whitespace")
    if "\n" in value or "\r" in value:
        errors.append(f"{prefix}: name must not contain a newline")
    return errors


def _validate_version(value: Any, prefix: str) -> list[str]:
    if not isinstance(value, str):
        return [f"{prefix}: version must be a string"]
    errors: list[str] = []
    if len(value) > 48:
        errors.append(f"{prefix}: version must be at most 48 characters")
    if VERSION_PATTERN.fullmatch(value) is None:
        errors.append(
            f"{prefix}: version must look like MAJOR.MINOR.PATCH, got {value!r}"
        )
    return errors


def _validate_capabilities(value: Any, prefix: str) -> list[str]:
    items, errors = _as_string_list(value, prefix, "capabilities")
    if items is None:
        return errors
    unknown = sorted({item for item in items if item not in VALID_CAPABILITIES})
    if unknown:
        errors.append(
            f"{prefix}: capabilities must be a subset of "
            f"{sorted(VALID_CAPABILITIES)}, got {unknown}"
        )
    repeated = _duplicates(items)
    if repeated:
        errors.append(
            f"{prefix}: capabilities must not contain duplicates: {repeated}"
        )
    return errors


def _validate_dependencies(value: Any, prefix: str) -> list[str]:
    """Shape only; references are a cross-entry rule (see ``validate_config``)."""

    items, errors = _as_string_list(value, prefix, "dependencies")
    if items is None:
        return errors
    empty = sorted({item for item in items if not item.strip()})
    if empty:
        errors.append(f"{prefix}: dependencies must not contain empty values")
    return errors


def _validate_permissions(value: Any, prefix: str) -> list[str]:
    items, errors = _as_string_list(value, prefix, "permissions")
    if items is None:
        return errors
    unknown = sorted({item for item in items if item not in VALID_PERMISSION_LEVELS})
    if unknown:
        errors.append(
            f"{prefix}: permissions must be a subset of "
            f"{sorted(VALID_PERMISSION_LEVELS)}, got {unknown}"
        )
    repeated = _duplicates(items)
    if repeated:
        errors.append(
            f"{prefix}: permissions must not contain duplicates: {repeated}"
        )
    # Declaration order carries no meaning; writes are canonicalised instead.
    return errors


def _validate_entry_repo(value: Any, prefix: str) -> list[str]:
    """Provenance only: never stat the path, the config is shared across machines."""

    if not isinstance(value, str):
        return [f"{prefix}: entry_repo must be a string"]
    errors: list[str] = []
    if not 1 <= len(value) <= 512:
        errors.append(f"{prefix}: entry_repo must be 1-512 characters")
    if value != value.strip():
        errors.append(f"{prefix}: entry_repo must not start or end with whitespace")
    if "\n" in value:
        errors.append(f"{prefix}: entry_repo must not contain a newline")
    return errors


def canonical_permissions(value: Any) -> Any:
    """Return permission levels in ascending scope order (write side only).

    Read paths never reorder and never write; only ``_save_config`` calls this
    so the tracked file has one stable shape (CMD-006 §1.4 rule 5).
    """

    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        return value
    fallback = len(SCOPE_LEVELS) + 1
    return sorted(value, key=lambda level: (SCOPE_LEVELS.get(level, fallback), level))


def validate_meta(meta: Any, file_label: str) -> list[str]:
    """Validate a file-level ``_meta`` block. Missing ``_meta`` is allowed."""

    if meta is None:
        return []
    if not isinstance(meta, dict):
        return [f"{file_label} _meta: must be an object"]

    prefix = f"{file_label} _meta"
    errors: list[str] = []

    for key in meta:
        if key not in META_FIELDS:
            errors.append(f"{prefix}: unknown field '{key}'")

    if "last_updated" in meta and not _is_iso_timestamp(meta["last_updated"]):
        errors.append(f"{prefix}: last_updated must be an ISO 8601 timestamp")

    if "total_modules" in meta:
        value = meta["total_modules"]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            errors.append(f"{prefix}: total_modules must be a non-negative integer")

    if "schema_version" in meta:
        value = meta["schema_version"]
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(
                f"{prefix}: schema_version must be an integer, got {value!r}"
            )
        elif value > SCHEMA_VERSION:
            # Classified by ``load_and_validate_config`` before field
            # validation; this message is the human-readable fallback for
            # callers that validate a mapping directly.
            errors.append(
                f"{prefix}: schema_version {value} is newer than this build "
                f"supports ({SCHEMA_VERSION})"
            )
        # values below SCHEMA_VERSION are legacy files this build still reads

    return errors


# --- Per-module validation ------------------------------------------------


def validate_config_module(module_id: str, entry: Any) -> list[str]:
    """Validate one config module entry. Returns a list of error messages."""

    errors: list[str] = []
    prefix = f"config module '{module_id}'"

    if not isinstance(entry, dict):
        errors.append(f"{prefix}: must be an object, got {type(entry).__name__}")
        return errors

    # Unknown fields.
    for key in entry:
        if key not in CONFIG_ALL_FIELDS:
            errors.append(f"{prefix}: unknown field '{key}'")

    # Required fields.
    for field in CONFIG_REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"{prefix}: missing required field '{field}'")

    # status.
    if "status" in entry and not (
        isinstance(entry["status"], str) and entry["status"] in PERSISTENT_STATUSES
    ):
        errors.append(
            f"{prefix}: status must be one of {sorted(PERSISTENT_STATUSES)}, "
            f"got {entry['status']!r}"
        )

    # transport + the entry point that transport requires.
    transport = entry.get("transport")
    # ``isinstance`` first: a list/dict here would raise TypeError on the
    # frozenset lookup and break the "status() never raises" contract.
    transport_known = isinstance(transport, str) and transport in VALID_TRANSPORTS
    if "transport" in entry and not transport_known:
        errors.append(
            f"{prefix}: transport must be one of {sorted(VALID_TRANSPORTS)}, "
            f"got {transport!r}"
        )

    if transport_known:
        required_entry_fields = TRANSPORT_ENTRY_FIELDS[transport]
        for field in sorted(required_entry_fields):
            if field not in entry:
                errors.append(
                    f"{prefix}: missing field '{field}' required for "
                    f"transport '{transport}'"
                )
        for field in sorted(TRANSPORT_ONLY_FIELDS - required_entry_fields):
            if field in entry:
                errors.append(
                    f"{prefix}: field '{field}' is not allowed for "
                    f"transport '{transport}'"
                )

    # command.
    if "command" in entry and not _non_empty_string_list(entry["command"]):
        errors.append(
            f"{prefix}: command must be a non-empty list of non-empty strings"
        )

    # description.
    if "description" in entry and not isinstance(entry["description"], str):
        errors.append(f"{prefix}: description must be a string")

    # updated_at.
    if "updated_at" in entry and not _is_iso_timestamp(entry["updated_at"]):
        errors.append(f"{prefix}: updated_at must be an ISO 8601 timestamp")

    # manifest fields — all optional; absent means "not declared yet".
    validators = {
        "name": _validate_name,
        "version": _validate_version,
        "capabilities": _validate_capabilities,
        "dependencies": _validate_dependencies,
        "permissions": _validate_permissions,
        "entry_repo": _validate_entry_repo,
    }
    for field, validate_field in validators.items():
        if field in entry:
            errors.extend(validate_field(entry[field], prefix))

    return errors


def validate_state_module(
    module_id: str, entry: Any, known_modules: set[str]
) -> list[str]:
    """Validate one state module entry."""

    errors: list[str] = []
    prefix = f"state module '{module_id}'"

    if module_id not in known_modules:
        errors.append(f"{prefix}: module not declared in config")

    if not isinstance(entry, dict):
        errors.append(f"{prefix}: must be an object, got {type(entry).__name__}")
        return errors

    # Unknown fields.
    for key in entry:
        if key not in STATE_ALL_FIELDS:
            errors.append(f"{prefix}: unknown field '{key}'")

    # Required fields.
    for field in STATE_REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"{prefix}: missing required field '{field}'")

    # status.
    if "status" in entry and not (
        isinstance(entry["status"], str) and entry["status"] in RUNTIME_STATUSES
    ):
        errors.append(
            f"{prefix}: status must be one of {sorted(RUNTIME_STATUSES)}, "
            f"got {entry['status']!r}"
        )

    # last_checked.
    if "last_checked" in entry and not _is_iso_timestamp(entry["last_checked"]):
        errors.append(f"{prefix}: last_checked must be an ISO 8601 timestamp")

    # response_time_ms.
    if "response_time_ms" in entry:
        value = entry["response_time_ms"]
        if value is not None and not isinstance(value, (int, float)):
            errors.append(f"{prefix}: response_time_ms must be a number or null")

    # last_error.
    if "last_error" in entry and not isinstance(
        entry["last_error"], (str, type(None))
    ):
        errors.append(f"{prefix}: last_error must be a string or null")

    return errors


# --- Whole-file validation ------------------------------------------------


def validate_config(modules: Any) -> list[str]:
    """Validate an entire config mapping (module_id -> entry)."""

    errors: list[str] = []

    if not isinstance(modules, dict):
        errors.append("config root must be an object")
        return errors

    for module_id, entry in modules.items():
        if module_id == "_meta":
            continue
        errors.extend(validate_config_module(module_id, entry))

    errors.extend(_validate_dependency_references(modules))
    errors.extend(validate_meta(modules.get("_meta"), "config"))

    return errors


def _validate_dependency_references(modules: dict[str, Any]) -> list[str]:
    """A dependency must name a module in this config, or shared infrastructure.

    Cross-entry because it needs the whole mapping; kept out of
    ``validate_merged`` which still has no production consumer (CMD-006 §1.9).
    """

    errors: list[str] = []
    module_ids = {
        module_id
        for module_id, entry in modules.items()
        if module_id != "_meta" and isinstance(entry, dict)
    }

    for module_id in module_ids:
        dependencies = modules[module_id].get("dependencies")
        if not isinstance(dependencies, list) or not all(
            isinstance(dependency, str) for dependency in dependencies
        ):
            continue  # shape is reported per entry
        for dependency in dependencies:
            if not dependency.strip():
                continue  # shape is reported per entry
            if dependency == module_id:
                errors.append(
                    f"config module '{module_id}': dependencies must not "
                    "include the module itself"
                )
            elif dependency not in module_ids and dependency not in INFRA_DEPENDENCIES:
                errors.append(
                    f"config module '{module_id}': unknown dependency "
                    f"'{dependency}' (must be a module id in this config or "
                    f"one of {sorted(INFRA_DEPENDENCIES)})"
                )

    return errors


def validate_state(
    state: Any, config_module_ids: set[str]
) -> list[str]:
    """Validate an entire state mapping against known config modules."""

    errors: list[str] = []

    if not isinstance(state, dict):
        errors.append("state root must be an object")
        return errors

    for module_id, entry in state.items():
        if module_id == "_meta":
            continue
        errors.extend(validate_state_module(module_id, entry, config_module_ids))

    errors.extend(validate_meta(state.get("_meta"), "state"))

    return errors


def validate_merged(config: dict[str, Any], state: dict[str, Any]) -> list[str]:
    """Cross-validate config + state together."""

    errors: list[str] = validate_config(config)

    config_ids = {
        module_id
        for module_id, entry in config.items()
        if module_id != "_meta" and isinstance(entry, dict)
    }

    errors.extend(validate_state(state, config_ids))

    return errors


# --- Load + validate helpers ----------------------------------------------


def read_json_document(path: Path) -> Any | None:
    """Read a JSON document.

    Returns ``None`` when the file does not exist (first run); raises
    ``RegistrySchemaError`` when the file exists but is not valid JSON or is
    not UTF-8. ``UnicodeDecodeError`` is a ``ValueError`` (not an
    ``OSError``/``JSONDecodeError``), so it needs its own handler: callers of
    this module only ever expect ``RegistrySchemaError`` from a bad read.
    """

    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None
    except UnicodeDecodeError as exc:
        raise RegistrySchemaError(f"{path} is not valid UTF-8: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RegistrySchemaError(f"{path} is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise RegistrySchemaError(f"{path} cannot be read: {exc}") from exc


def _declared_schema_version(document: Any) -> int:
    """Return the schema version a config declares; absent/unusable means legacy.

    A wrong type is not a downgrade — ``validate_meta`` reports it as a normal
    field error, so this helper never turns a typo into a version refusal.
    """

    if not isinstance(document, dict):
        return LEGACY_SCHEMA_VERSION
    meta = document.get("_meta")
    if not isinstance(meta, dict):
        return LEGACY_SCHEMA_VERSION
    version = meta.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int):
        return LEGACY_SCHEMA_VERSION
    return version


def load_and_validate_config(path: Path) -> dict[str, Any]:
    """Load config JSON and validate it.

    The declared ``_meta.schema_version`` is checked *before* any field, so a
    file from a newer build fails once with one actionable message instead of
    drowning the user in "unknown field" noise (CMD-006 §1.8, §2.4).

    Raises ``RegistryDowngradeError`` when the file is newer than this build
    and ``RegistrySchemaError`` on any other violation. Returns ``{}`` if the
    file does not exist yet (first run).
    """

    data = read_json_document(path)
    if data is None:
        if path.exists():
            raise RegistrySchemaError(f"{path} root must be an object")
        return {}

    declared = _declared_schema_version(data)
    if declared > SCHEMA_VERSION:
        raise RegistryDowngradeError(
            f"{path} was written by a newer config schema "
            f"(schema_version {declared}; this build supports {SCHEMA_VERSION}). "
            "Refusing to overwrite it. Restore the config or revert the upgrade "
            "commit — see docs/runbooks/registry-schema-rollback.md"
        )

    errors = validate_config(data)
    if errors:
        raise RegistrySchemaError("; ".join(errors))

    return data

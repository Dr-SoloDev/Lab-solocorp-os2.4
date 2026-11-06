#!/usr/bin/env python3
"""Repair a module registry config that is newer than the code reading it.

Recovery step 2b of ``docs/runbooks/registry-schema-rollback.md``. Use it when
``git revert`` of the paired upgrade commit is not possible — typically because
a module was registered after the upgrade, and reverting would drop that entry.

What it does, and only this:

* removes entry fields that the target schema does not know about
  (e.g. ``permissions`` when going back to schema 1),
* keeps every module entry exactly as it is otherwise,
* sets ``_meta.schema_version`` (and ``total_modules``) when ``_meta`` exists,
* writes atomically (temp file + ``os.replace``), never through the registry
  code — the current code is exactly what is refusing to read this file.

It never touches the state file (state is derived and rewrites itself).

Dry run by default: prints the diff and exits. ``--yes`` performs the write.

Usage::

    python scripts/registry-repair.py --to-schema 1 --keep-modules
    python scripts/registry-repair.py --to-schema 1 --keep-modules --yes
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config" / "module-registry.json"

# Entry fields introduced after schema 1. Frozen here on purpose: a repair tool
# must keep working when the live schema grows, so it does not import the
# schema module it is trying to roll back past.
FIELDS_ADDED_IN: dict[int, frozenset[str]] = {
    2: frozenset(
        {"name", "version", "capabilities", "dependencies", "permissions", "entry_repo"}
    ),
}
MAX_KNOWN_SCHEMA = max(FIELDS_ADDED_IN)


def fields_after(target: int) -> frozenset[str]:
    """Fields the target schema does not know about."""

    offending: set[str] = set()
    for version, fields in FIELDS_ADDED_IN.items():
        if version > target:
            offending |= fields
    return frozenset(offending)


def repair(document: dict[str, Any], target: int) -> tuple[dict[str, Any], list[str]]:
    """Return ``(repaired_document, stripped_field_paths)``.

    Module entries are preserved; only fields the target schema cannot read are
    removed, plus the ``_meta`` version markers.
    """

    forbidden = fields_after(target)
    modules: dict[str, Any] = {}
    stripped: list[str] = []

    for module_id, entry in document.items():
        if module_id == "_meta":
            continue
        if not isinstance(entry, dict):
            modules[module_id] = entry
            continue
        kept = {}
        for field, value in entry.items():
            if field in forbidden:
                stripped.append(f"{module_id}.{field}")
            else:
                kept[field] = value
        modules[module_id] = kept

    meta = document.get("_meta")
    module_count = len(modules)
    if isinstance(meta, dict):
        modules["_meta"] = {
            **meta,
            "schema_version": target,
            "total_modules": module_count,
        }

    return modules, sorted(stripped)


def _dump(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def _atomic_write(path: Path, text: str) -> None:
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
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except BaseException:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Strip config fields a target registry schema cannot read."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"config file to repair (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--to-schema",
        type=int,
        required=True,
        help="target on-disk schema version (downgrade target)",
    )
    parser.add_argument(
        "--keep-modules",
        action="store_true",
        help="keep every module entry (the only supported mode)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="write the repair (default is a dry run that only prints)",
    )
    args = parser.parse_args(argv)

    if args.to_schema < 1:
        print(f"error: --to-schema must be >= 1, got {args.to_schema}", file=sys.stderr)
        return 2
    if args.to_schema > MAX_KNOWN_SCHEMA:
        print(
            f"error: --to-schema {args.to_schema} is newer than this tool knows "
            f"({MAX_KNOWN_SCHEMA}); refusing to write a config this build cannot read",
            file=sys.stderr,
        )
        return 2

    path: Path = args.path
    if not path.exists():
        print(f"error: config file {path} does not exist", file=sys.stderr)
        return 2
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(document, dict):
        print(f"error: {path} root must be an object", file=sys.stderr)
        return 2

    repaired, stripped = repair(document, args.to_schema)
    before = _dump(document)
    after = _dump(repaired)

    if before == after:
        print(f"{path}: already at schema {args.to_schema}; nothing to strip")
        return 0

    if stripped:
        print(f"removing {len(stripped)} field(s) unknown to schema {args.to_schema}:")
        for field in stripped:
            print(f"  - {field}")
    if not args.keep_modules:
        print("note: module entries are always preserved; --keep-modules is the default")

    print(
        "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=str(path),
                tofile=f"{path} (schema {args.to_schema})",
            )
        )
    )

    if not args.yes:
        print("dry run — nothing written. Re-run with --yes to apply.")
        return 0

    _atomic_write(path, after)
    print(f"wrote {path} at schema {args.to_schema}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

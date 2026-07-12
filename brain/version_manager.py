"""
WP4: Evolution Brain System — Brain File Version Manager
Owner: @architect-songsak (พี่ทรงศักดิ์)

Manages versioned backups of brain files under brain/versions/<slug>/.
Supports backup, rollback, list, and intelligent merge operations.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

BRAIN_DIR = Path(__file__).resolve().parent
VERSIONS_DIR = BRAIN_DIR / "versions"


def _ensure_versions_dir(slug):
    """Create versions/<slug> directory if it doesn't exist."""
    slug_dir = VERSIONS_DIR / slug
    slug_dir.mkdir(parents=True, exist_ok=True)
    return slug_dir


def _brain_path(slug):
    """Resolve the brain file path for a given slug."""
    # Check common brain file patterns
    candidates = [
        BRAIN_DIR / slug,
        BRAIN_DIR / f"{slug}.md",
        BRAIN_DIR / f"{slug}.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Default — try as-is
    return BRAIN_DIR / slug


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(slug):
    """
    Copy the current brain file for *slug* into versions/<slug>/ with a timestamp.

    Args:
        slug: Name of the brain file (e.g. 'ceo-identity', 'learnt')

    Returns:
        Path to the backup file, or None if the source doesn't exist.
    """
    src = _brain_path(slug)
    if not src.exists():
        print(f"[version_manager] WARN: '{slug}' not found in {BRAIN_DIR}")
        return None

    slug_dir = _ensure_versions_dir(slug)
    ts = _timestamp()
    ext = src.suffix or ".bak"
    backup_path = slug_dir / f"{src.stem}-{ts}{ext}"
    shutil.copy2(src, backup_path)
    print(f"[version_manager] ✅ Backed up '{slug}' → {backup_path}")
    return backup_path


def rollback(slug, version):
    """
    Restore a brain file from a specific version backup.

    Args:
        slug: Name of the brain file.
        version: Version identifier — can be a timestamp string
                 ('20260708_143022') or a partial filename.
                 Use 'list' as version to see available versions.

    Returns:
        True on success, False if the version doesn't exist.
    """
    slug_dir = VERSIONS_DIR / slug
    if not slug_dir.exists():
        print(f"[version_manager] ❌ No versions found for '{slug}'")
        return False

    if version == "latest":
        backups = sorted(slug_dir.iterdir(), key=os.path.getmtime)
        if not backups:
            print(f"[version_manager] ❌ No backups for '{slug}'")
            return False
        chosen = backups[-1]
    else:
        matches = list(slug_dir.glob(f"*{version}*"))
        if not matches:
            print(f"[version_manager] ❌ No backup matching '{version}' for '{slug}'")
            list_versions(slug)
            return False
        chosen = matches[0]

    dst = _brain_path(slug)
    shutil.copy2(chosen, dst)
    print(f"[version_manager] ✅ Rolled back '{slug}' → {chosen.name}")
    return True


def list_versions(slug):
    """
    Print all available version backups for *slug*.

    Args:
        slug: Name of the brain file.

    Returns:
        List of Path objects for the available backups (empty list if none).
    """
    slug_dir = VERSIONS_DIR / slug
    if not slug_dir.exists():
        print(f"[version_manager] No versions found for '{slug}'")
        return []

    backups = sorted(slug_dir.iterdir(), key=os.path.getmtime, reverse=True)
    if not backups:
        print(f"[version_manager] No versions found for '{slug}'")
        return []

    print(f"[version_manager] Available versions for '{slug}':")
    for i, bp in enumerate(backups, 1):
        size = bp.stat().st_size
        mtime = datetime.fromtimestamp(bp.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  {i}. {bp.name}  ({size:,} bytes, {mtime})")
    return backups


def merge(slug, new_content):
    """
    Merge new content into a brain file without overwriting existing data.

    - For .json files: perform a deep merge (dict keys are unioned, lists concatenated).
    - For .md files: append new sections under a timestamped header,
      deduplicating lines that already exist in the file.
    - For other files: append new content after a separator.

    Args:
        slug: Name of the brain file.
        new_content: String content to merge in.

    Returns:
        True on success, False on error.
    """
    src = _brain_path(slug)
    if not src.exists():
        # File doesn't exist — just write it
        src.write_text(new_content, encoding="utf-8")
        print(f"[version_manager] ✅ Created '{slug}' with new content")
        return True

    ext = src.suffix.lower()

    try:
        if ext == ".json":
            return _merge_json(src, new_content)
        elif ext == ".md":
            return _merge_md(src, new_content)
        else:
            return _merge_raw(src, new_content)
    except Exception as e:
        print(f"[version_manager] ❌ Merge failed for '{slug}': {e}")
        return False


def _merge_json(path, new_content):
    """Deep-merge JSON: union of keys, concatenate lists."""
    with open(path, "r", encoding="utf-8") as f:
        existing = json.load(f)

    incoming = json.loads(new_content) if isinstance(new_content, str) else new_content

    merged = _deep_merge(existing, incoming)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"[version_manager] ✅ Merged JSON content into '{path.name}'")
    return True


def _deep_merge(base, update):
    """Recursive dict merge. Lists are concatenated; scalars prefer update."""
    result = base.copy()
    for key, value in update.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = _deep_merge(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                # Concatenate, deduplicating
                seen = set()
                merged = []
                for item in result[key] + value:
                    item_str = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
                    if item_str not in seen:
                        seen.add(item_str)
                        merged.append(item)
                result[key] = merged
            else:
                # new value wins for scalars
                result[key] = value
        else:
            result[key] = value
    return result


def _merge_md(path, new_content):
    """Append new sections to markdown under a timestamped header, deduplicating lines."""
    existing = path.read_text(encoding="utf-8")
    existing_lines = existing.split("\n")
    new_lines = new_content.split("\n")

    # Filter new lines that already exist in the file (trimmed)
    existing_trimmed = {line.strip() for line in existing_lines}
    unique_new = [line for line in new_lines if line.strip() not in existing_trimmed]

    if not unique_new:
        print(f"[version_manager] ℹ️ No new content to merge into '{path.name}' — all lines already present")
        return True

    ts = _timestamp()
    separator = f"\n---\n## Merge {ts}\n\n"
    merged_text = existing.rstrip("\n") + separator + "\n".join(unique_new) + "\n"

    path.write_text(merged_text, encoding="utf-8")
    print(f"[version_manager] ✅ Merged {len(unique_new)} new lines into '{path.name}'")
    return True


def _merge_raw(path, new_content):
    """Append new content after a timestamped separator for non-structured files."""
    ts = _timestamp()
    separator = f"\n# === MERGE {ts} ===\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(separator)
        f.write(new_content)
        if not new_content.endswith("\n"):
            f.write("\n")
    print(f"[version_manager] ✅ Appended content to '{path.name}'")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage:")
        print("  python version_manager.py backup <slug>")
        print("  python version_manager.py rollback <slug> <version>")
        print("  python version_manager.py list <slug>")
        print("  python version_manager.py merge <slug> <file>")
        sys.exit(1)

    command = sys.argv[1]
    slug = sys.argv[2]

    if command == "backup":
        backup(slug)
    elif command == "rollback":
        version = sys.argv[3] if len(sys.argv) > 3 else "latest"
        rollback(slug, version)
    elif command == "list":
        list_versions(slug)
    elif command == "merge":
        filepath = sys.argv[3]
        content = Path(filepath).read_text(encoding="utf-8")
        merge(slug, content)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

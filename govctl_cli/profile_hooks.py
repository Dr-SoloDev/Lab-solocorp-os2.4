"""
Profile Governance Hook Generator — เพิ่ม governance checkpoint ในทุก profile SOUL.md

Usage:
    from govctl_cli.profile_hooks import add_gov_checkpoint, verify_gov_hooks

    # Add checkpoint to a single profile
    diff = add_gov_checkpoint("profiles/07-engineering/SOUL.md")

    # Scan all profiles for compliance
    report = verify_gov_hooks()
"""

import os
import re
from pathlib import Path
from difflib import unified_diff


# ---------------------------------------------------------------------------
# The governance snippet to inject
# ---------------------------------------------------------------------------
GOV_CHECKPOINT_MARKER = "## 🏛️ Governance Checkpoint"

GOV_CHECKPOINT_SNIPPET = """
## 🏛️ Governance Checkpoint

ก่อนเริ่ม task หรือ proposal ใด ๆ ที่ส่งผลต่อระบบ:
1. **ประเมิน Complexity** — ใช้ `./govctl threshold assess` (RFC-001 Matrix)
2. **ตรวจสอบ Governance Status** — ดู ADR/RFC/Guard ที่เกี่ยวข้องผ่าน `./govctl status`
3. **ถ้าต้องสร้าง artifact ใหม่** — ใช้ `./govctl adr new` หรือ `./govctl rfc new`
4. **รอให้ Orchestrator ยืนยัน Guard gates** ก่อน execute (สำหรับ `full_review`)

> ดูรายละเอียด governance เต็มได้ที่ `profiles/04-orchestrator/SOUL.md` section Governance Integration

"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_insertion_point(lines: list[str]) -> int | None:
    """Find the best line to insert the governance checkpoint.

    Priority (line index descending — insert AFTER):
      1. ``## Rules`` section heading
      2. ``## Core Discipline`` section heading
      3. ``Other`` | ``---`` separator just before Context Reference
      4. Last heading before ``## 🗺️ Context Reference``
    """
    # Find Context Reference boundary
    ctx_line = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s*🗺️\s*Context\s*Reference", line):
            ctx_line = i
            break

    # 1. Rules section
    for i, line in enumerate(lines):
        if re.match(r"^##\s*Rules\s*$", line) and (ctx_line is None or i < ctx_line):
            # Find the last non-blank line after ## Rules but before next ## or ---
            j = i + 1
            while j < len(lines) and not lines[j].startswith("## ") and lines[j].strip() != "---":
                j += 1
            # Move back past blank lines
            k = j - 1
            while k > i and lines[k].strip() == "":
                k -= 1
            return k + 1  # Insert after last content line of Rules

    # 2. Core Discipline
    for i, line in enumerate(lines):
        if re.match(r"^##\s*Core\s*Discipline", line) and (ctx_line is None or i < ctx_line):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("## ") and lines[j].strip() != "---":
                j += 1
            k = j - 1
            while k > i and lines[k].strip() == "":
                k -= 1
            return k + 1

    # 3. Before Context Reference or at end
    if ctx_line is not None:
        # Check if there's a blank line or --- just before
        before = ctx_line - 1
        while before >= 0 and lines[before].strip() in ("", "---"):
            before -= 1
        return before + 1

    return len(lines)  # Append to end


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_gov_checkpoint(profile_path: str, dry_run: bool = False) -> str:
    """Add a governance checkpoint to a profile SOUL.md.

    Args:
        profile_path: Path to the SOUL.md file (relative or absolute).
        dry_run: If True, return diff without modifying the file.

    Returns:
        Unified diff string showing changes (or would-be changes).

    Raises:
        FileNotFoundError: If the profile path does not exist.
    """
    path = Path(profile_path)
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path.resolve()}")

    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    # Check if checkpoint already exists
    if GOV_CHECKPOINT_MARKER in original:
        return "✅ Governance checkpoint already present — no change needed."

    insert_at = _find_insertion_point(lines)

    # Insert snippet
    snippet_lines = GOV_CHECKPOINT_SNIPPET.splitlines(keepends=True)
    modified = lines[:insert_at] + snippet_lines + lines[insert_at:]

    # Build diff
    diff = "".join(
        unified_diff(
            lines,
            modified,
            fromfile=str(path),
            tofile=str(path),
            lineterm="",
        )
    )

    if not dry_run:
        path.write_text("".join(modified), encoding="utf-8")

    return diff or "(no diff — content unchanged)"


def verify_gov_hooks(profiles_dir: str = "profiles") -> list[dict]:
    """Scan all profiles and report governance hook status.

    Args:
        profiles_dir: Path to the profiles directory (default ``profiles``).

    Returns:
        List of dicts, one per profile, keyed by:
          - path (str): relative path to SOUL.md
          - has_hook (bool): whether governance checkpoint is present
          - status (str): ``ok`` | ``missing`` | ``not_found``
    """
    base = Path(profiles_dir)
    if not base.is_dir():
        return [{"path": str(base), "has_hook": False, "status": "not_found"}]

    results: list[dict] = []

    # Scan all sub-directories in profiles/ for SOUL.md
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        soul_path = entry / "SOUL.md"
        if not soul_path.exists():
            results.append({
                "path": str(soul_path.relative_to(base.parent)),
                "has_hook": False,
                "status": "not_found",
            })
            continue

        content = soul_path.read_text(encoding="utf-8")
        has_hook = GOV_CHECKPOINT_MARKER in content

        results.append({
            "path": str(soul_path.relative_to(base.parent)),
            "has_hook": has_hook,
            "status": "ok" if has_hook else "missing",
        })

    return results


# ---------------------------------------------------------------------------
# CLI — plug into govctl as ``govctl hook``
# ---------------------------------------------------------------------------

import typer

hook_app = typer.Typer(
    name="hook",
    help="Profile governance hook management",
)


@hook_app.command("add")
def hook_add(
    profile: str = typer.Argument(..., help="Path to SOUL.md, e.g. profiles/07-engineering/SOUL.md"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show diff only, don't write"),
):
    """Add a governance checkpoint to a profile SOUL.md."""
    try:
        diff = add_gov_checkpoint(profile, dry_run=dry_run)
        if diff.startswith("✅"):
            typer.echo(diff)
        else:
            typer.echo(f"\n{diff}\n")
            if dry_run:
                typer.echo("⚠️  Dry-run — file NOT modified.")
            else:
                typer.echo("✅ Checkpoint added.")
    except FileNotFoundError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(code=1)


@hook_app.command("verify")
def hook_verify(
    profiles_dir: str = typer.Option("profiles", "--dir", "-d", help="Profiles directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all profiles"),
):
    """Scan all profiles and report governance hook compliance."""
    report = verify_gov_hooks(profiles_dir)

    if not report:
        typer.echo("❌ No profiles found.")
        raise typer.Exit(code=1)

    ok = [r for r in report if r["status"] == "ok"]
    missing = [r for r in report if r["status"] == "missing"]
    not_found = [r for r in report if r["status"] == "not_found"]

    typer.echo(f"\n📋 Governance Hook Scan — {profiles_dir}/")
    typer.echo("=" * 50)

    if verbose:
        for r in report:
            icon = {"ok": "✅", "missing": "⚠️", "not_found": "❌"}
            typer.echo(f"  {icon[r['status']]} {r['path']}")

    typer.echo(f"\n  ✅ {len(ok)} profiles with governance hooks")
    typer.echo(f"  ⚠️  {len(missing)} profiles MISSING governance hooks")
    if not_found:
        typer.echo(f"  ❌ {len(not_found)} profiles missing SOUL.md entirely")

    if missing:
        typer.echo("\nRun the following to add hooks:")
        for r in missing:
            typer.echo(f"  ./govctl hook add {r['path']}")


# ===================================================================
# AO Agent Integration Hooks
# ===================================================================

AO_CHECKPOINT_MARKER = "### AO Agent Integration"

# Mapping: profile_id → AO agent ID
try:
    from govctl_cli.ao.agents import PROFILE_TO_AGENT as _P2A

    def _get_ao_agent_for(path_str: str) -> str:
        """Determine AO agent ID from a profile path like profiles/07-engineering/SOUL.md."""
        # Extract the NN-name prefix from the path
        parts = path_str.replace("\\", "/").split("/")
        for part in parts:
            if re.match(r"^\d{2}-", part):
                profile_id = part
                if profile_id in _P2A:
                    return _P2A[profile_id]
        # Fallback: orchestrator for unknown profiles
        return "orchestrator"

    _AO_AVAILABLE = True
except ImportError:
    _AO_AVAILABLE = False

    def _get_ao_agent_for(path_str: str) -> str:
        return "orchestrator"


AO_CHECKPOINT_SNIPPET = """
### AO Agent Integration
- เมื่อต้องการคำปรึกษาหรือดำเนินการที่เกี่ยวกับ AO agent ที่รับผิดชอบ → ใช้ `govctl ao run <agent_id>`
- AO agent: `{agent_id}` | Status: 🔴 รอ Implement
"""


def add_ao_hook(profile_path: str, dry_run: bool = False) -> str:
    """Add an AO integration checkpoint to a profile SOUL.md.

    Args:
        profile_path: Path to the SOUL.md file (relative or absolute).
        dry_run: If True, return diff without modifying the file.

    Returns:
        Unified diff string showing changes (or would-be changes).

    Raises:
        FileNotFoundError: If the profile path does not exist.
    """
    path = Path(profile_path)
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path.resolve()}")

    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    # Check if AO checkpoint already exists
    if AO_CHECKPOINT_MARKER in original:
        return "✅ AO integration checkpoint already present — no change needed."

    # Determine AO agent for this profile
    agent_id = _get_ao_agent_for(str(path))

    # Inject snippet
    snippet_text = AO_CHECKPOINT_SNIPPET.format(agent_id=agent_id)
    insert_at = _find_insertion_point(lines)
    snippet_lines = snippet_text.splitlines(keepends=True)
    modified = lines[:insert_at] + snippet_lines + lines[insert_at:]

    diff = "".join(
        unified_diff(
            lines,
            modified,
            fromfile=str(path),
            tofile=str(path),
            lineterm="",
        )
    )

    if not dry_run:
        path.write_text("".join(modified), encoding="utf-8")

    return diff or "(no diff — content unchanged)"


def verify_ao_hooks(profiles_dir: str = "profiles") -> list[dict]:
    """Scan all profiles and report AO integration hook status.

    Args:
        profiles_dir: Path to the profiles directory (default ``profiles``).

    Returns:
        List of dicts, one per profile, keyed by:
          - path (str): relative path to SOUL.md
          - has_ao_hook (bool): whether AO checkpoint is present
          - agent_id (str): the AO agent this profile maps to
          - status (str): ``ok`` | ``missing`` | ``not_found``
    """
    base = Path(profiles_dir)
    if not base.is_dir():
        return [{"path": str(base), "has_ao_hook": False, "agent_id": "", "status": "not_found"}]

    results: list[dict] = []

    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        soul_path = entry / "SOUL.md"
        rel_path = str(soul_path.relative_to(base.parent))
        profile_id = entry.name  # e.g. "07-engineering"

        if not soul_path.exists():
            results.append({
                "path": rel_path,
                "has_ao_hook": False,
                "agent_id": _get_ao_agent_for(profile_id),
                "status": "not_found",
            })
            continue

        content = soul_path.read_text(encoding="utf-8")
        has_ao_hook = AO_CHECKPOINT_MARKER in content
        agent_id = _get_ao_agent_for(profile_id) if _AO_AVAILABLE else "orchestrator"

        results.append({
            "path": rel_path,
            "has_ao_hook": has_ao_hook,
            "agent_id": agent_id,
            "status": "ok" if has_ao_hook else "missing",
        })

    return results


# ── CLI commands for AO hooks ────────────────────────────────────────


@hook_app.command("ao-add")
def hook_ao_add(
    profile: str = typer.Argument(..., help="Path to SOUL.md, e.g. profiles/07-engineering/SOUL.md"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show diff only, don't write"),
):
    """Add an AO integration checkpoint to a profile SOUL.md."""
    if not _AO_AVAILABLE:
        typer.echo("⚠️  AO module not available — run 'pip install -e .' from govctl_cli/")
        raise typer.Exit(code=1)

    try:
        diff = add_ao_hook(profile, dry_run=dry_run)
        if diff.startswith("✅"):
            typer.echo(diff)
        else:
            typer.echo(f"\n{diff}\n")
            if dry_run:
                typer.echo("⚠️  Dry-run — file NOT modified.")
            else:
                typer.echo("✅ AO checkpoint added.")
    except FileNotFoundError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(code=1)


@hook_app.command("ao-verify")
def hook_ao_verify(
    profiles_dir: str = typer.Option("profiles", "--dir", "-d", help="Profiles directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all profiles"),
):
    """Scan all profiles and report AO integration hook compliance."""
    report = verify_ao_hooks(profiles_dir)

    if not report:
        typer.echo("❌ No profiles found.")
        raise typer.Exit(code=1)

    ok = [r for r in report if r["status"] == "ok"]
    missing = [r for r in report if r["status"] == "missing"]
    not_found = [r for r in report if r["status"] == "not_found"]

    typer.echo(f"\n🤖 AO Integration Hook Scan — {profiles_dir}/")
    typer.echo("=" * 50)

    if verbose:
        for r in report:
            icon = {"ok": "✅", "missing": "⚠️", "not_found": "❌"}
            typer.echo(f"  {icon[r['status']]} {r['path']:45s} → {r['agent_id']}")

    typer.echo(f"\n  ✅ {len(ok)} profiles with AO hooks")
    typer.echo(f"  ⚠️  {len(missing)} profiles MISSING AO hooks")
    if not_found:
        typer.echo(f"  ❌ {len(not_found)} profiles missing SOUL.md entirely")

    if missing:
        typer.echo("\nRun the following to add AO hooks:")
        for r in missing:
            typer.echo(f"  ./govctl hook ao-add {r['path']}")

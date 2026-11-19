"""Worktree MCP Contract — pytest port of the fix/worktree-preflight-root harness.

Contract under test (commit 56555ac): a main checkout may keep `.venv` as a real
directory (`ok_real_dir`); a linked worktree must symlink it (`ok`), and a real
directory there is `not_symlink` with a `mv … .bak-<ts>` fix — never `rm -rf`.
`opencode.json(c)` must not keep a relative `".venv/bin/python3"`, and neither
shipped script may contain `rm -rf`, `rmdir`, `unlink` or a bare `rm `.

Self-contained: throwaway git repos under `tmp_path`; host worktrees untouched.
The two tests running `scripts/worktree-setup.sh` skip when its hard-coded
canonical venv is absent (CI).
"""

import importlib.util
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
BOOTSTRAP, SETUP_SH = SCRIPTS / "session-bootstrap.py", SCRIPTS / "worktree-setup.sh"

# Hard-coded inside scripts/worktree-setup.sh (its pre-check exits 1 without it).
HOST_CANONICAL_PY = Path("/data/projects/Lab-solocorp-os2.4/.venv/bin/python3")
requires_host_venv = pytest.mark.skipif(
    not HOST_CANONICAL_PY.exists(), reason="canonical venv absent (CI)"
)


def _git(repo: Path, *args: str) -> None:
    """Run git without depending on the host's user.name/user.email."""
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_venv(path: Path) -> None:
    """Structurally valid venv: <path>/bin/python3 exists and is executable."""
    py = path / "bin" / "python3"
    py.parent.mkdir(parents=True)
    py.write_text("#!/bin/sh\nexit 0\n")
    py.chmod(0o755)


@pytest.fixture
def main_repo(tmp_path):
    """Main checkout: git repo with a real, working .venv directory."""
    repo = tmp_path / "main"
    repo.mkdir()
    _git(repo, "init", "-q")
    who = ["-c", "user.email=t@example.invalid", "-c", "user.name=T"]
    _git(repo, *who, "commit", "--allow-empty", "-q", "-m", "init")
    make_venv(repo / ".venv")
    return repo


def linked_worktree(main: Path, name: str) -> Path:
    wt = main.parent / name
    _git(main, "worktree", "add", str(wt), "-b", name)
    return wt


def load_bootstrap(repo: Path, canonical_venv: Path | None = None):
    """Import session-bootstrap.py with BASE/CANONICAL_* repointed to `repo`.

    They are module globals read at call time, so overriding them isolates the
    module from the host; for a linked worktree the canonical venv is the main
    checkout's `.venv` (the symlink target).
    """
    spec = importlib.util.spec_from_file_location("sb_under_test", BOOTSTRAP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    venv = canonical_venv or repo / ".venv"
    mod.BASE, mod.CANONICAL_VENV = repo, venv
    mod.CANONICAL_PY = venv / "bin" / "python3"
    return mod


def run_fix_only(repo: Path) -> tuple[int, str]:
    """Copy the setup script into `repo` and run its --fix-only mode."""
    script = repo / "scripts" / "worktree-setup.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SETUP_SH, script)
    cmd = ["bash", str(script), "--fix-only"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def test_main_checkout_real_venv_passes(main_repo):
    """Main checkout + real .venv dir = valid, no destructive advice."""
    result = load_bootstrap(main_repo).preflight_venv()
    assert result["ok"] is True
    assert result["status"] == "ok_real_dir"
    assert "rm -rf" not in result["fix"]


def test_linked_worktree_correct_symlink_passes(main_repo):
    """Linked worktree + .venv -> <main>/.venv = contract satisfied."""
    wt = linked_worktree(main_repo, "wt-symlink")
    (wt / ".venv").symlink_to(main_repo / ".venv")
    result = load_bootstrap(wt, main_repo / ".venv").preflight_venv()
    assert result["ok"] is True
    assert result["status"] == "ok"


def test_linked_worktree_real_dir_gets_mv_hint(main_repo):
    """Linked worktree + real .venv dir = fail; the fix moves, never deletes."""
    wt = linked_worktree(main_repo, "wt-realdir")
    make_venv(wt / ".venv")
    result = load_bootstrap(wt, main_repo / ".venv").preflight_venv()
    assert result["ok"] is False
    assert result["status"] == "not_symlink"
    assert result["fix"].startswith("mv ")
    assert ".bak-" in result["fix"]
    assert "rm -rf" not in result["fix"]


def test_config_relative_path_flagged(main_repo):
    """Relative .venv/bin/python3 is flagged; the absolute form passes."""
    sb = load_bootstrap(main_repo)
    cfg = main_repo / "opencode.json"
    cfg.write_text('{"mcp": {"x": {"command": [".venv/bin/python3", "-m", "x"]}}}\n')
    flagged = sb.preflight_mcp_config()
    assert flagged["ok"] is False
    assert flagged["status"] == "relative_found"
    absolute = sb.CANONICAL_VENV / "bin" / "python3"
    cfg.write_text('{"mcp": {"x": {"command": ["%s", "-m", "x"]}}}\n' % absolute)
    assert sb.preflight_mcp_config()["ok"] is True


def test_scripts_have_no_destructive_commands():
    """Neither shipped script may suggest or contain a destructive command."""
    for path in (BOOTSTRAP, SETUP_SH):
        text = path.read_text(encoding="utf-8")
        assert "rm -rf" not in text, path
        assert not re.search(r"\b(rmdir|unlink)\b", text), path
        assert not re.search(r"\brm\s", text), path


@requires_host_venv
def test_fix_only_main_checkout_is_noop(main_repo):
    """--fix-only on a main checkout refuses to touch a working real .venv."""
    rc, out = run_fix_only(main_repo)
    assert rc == 0
    assert "โฟลเดอร์หลัก" in out
    assert "rm -rf" not in out


@requires_host_venv
def test_fix_only_linked_real_dir_exits_1_with_mv(main_repo):
    """--fix-only on a linked worktree with a real .venv dir fails with a mv fix."""
    wt = linked_worktree(main_repo, "wt-fix-only")
    make_venv(wt / ".venv")
    rc, out = run_fix_only(wt)
    assert rc == 1
    assert "mv " in out
    assert ".bak-" in out
    assert "rm -rf" not in out

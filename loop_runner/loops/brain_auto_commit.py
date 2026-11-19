import subprocess
from pathlib import Path
from datetime import timedelta
from ..runner import Loop

import os
_REPO = os.environ.get("SOLOCORP_REPO", str(Path(__file__).parent.parent.parent))


def _git(cmd: list[str]) -> str:
    r = subprocess.run(["git", "-C", _REPO] + cmd, capture_output=True, text=True)
    return r.stdout.strip()


_BRAIN_DIRS = ("brain/", "memory/", "bus/", ".claude/", "decisions/")


def _is_brain_path(path: str) -> bool:
    """Only top-level brain-owned dirs, matched at the start of the path.

    Anchoring matters: a substring test made "bus/" match "central_bus/…",
    so the loop swept source code and raw media into commit 64344c4.
    """
    return path.startswith(_BRAIN_DIRS)


def _status_path(line: str) -> str:
    """Stageable path from one `git status --porcelain` line.

    Porcelain v1 is "XY path". A rename is "XY old -> new" — stage the
    destination. Quoted paths (spaces/non-ASCII) are unquoted.
    """
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path.strip().strip('"')


class BrainAutoCommitLoop(Loop):
    loop_id = "brain_auto_commit"
    interval = timedelta(hours=1)
    trust_level = 4  # L4 — auto commit + push
    model_hint = "glm-5.2"  # cron — git ops only, no AI call

    def run(self) -> str:
        status = _git(["status", "--porcelain"])
        if not status:
            return "✅ brain-auto-commit: nothing to commit"

        changed_files = [
            _status_path(line) for line in status.splitlines() if line.strip()
        ]
        # Only auto-commit brain/memory files — not source code
        brain_files = [f for f in changed_files if _is_brain_path(f)]
        if not brain_files:
            return f"⏭ brain-auto-commit: {len(changed_files)} changes but none are brain files — skip"

        for f in brain_files:
            _git(["add", f])
        _git(["commit", "-m", f"chore(brain): auto-commit {len(brain_files)} brain files"])
        push = _git(["push"])
        return f"✅ brain-auto-commit: committed {len(brain_files)} files\n{push}"

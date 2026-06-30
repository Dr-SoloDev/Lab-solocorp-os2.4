import subprocess
from pathlib import Path
from datetime import timedelta
from ..runner import Loop

import os
_REPO = os.environ.get("SOLOCORP_REPO", str(Path(__file__).parent.parent.parent))


def _git(cmd: list[str]) -> str:
    r = subprocess.run(["git", "-C", _REPO] + cmd, capture_output=True, text=True)
    return r.stdout.strip()


class BrainAutoCommitLoop(Loop):
    loop_id = "brain_auto_commit"
    interval = timedelta(hours=1)
    trust_level = 4  # L4 — auto commit + push
    model_hint = "glm-5.2"  # cron — git ops only, no AI call

    def run(self) -> str:
        status = _git(["status", "--porcelain"])
        if not status:
            return "✅ brain-auto-commit: nothing to commit"

        changed_files = [line[3:] for line in status.splitlines() if line.strip()]
        # Only auto-commit brain/memory files — not source code
        brain_files = [f for f in changed_files if any(
            p in f for p in ("memory/", "bus/", ".claude/", "decisions/", "brain/")
        )]
        if not brain_files:
            return f"⏭ brain-auto-commit: {len(changed_files)} changes but none are brain files — skip"

        for f in brain_files:
            _git(["add", f])
        _git(["commit", "-m", f"chore(brain): auto-commit {len(brain_files)} brain files"])
        push = _git(["push"])
        return f"✅ brain-auto-commit: committed {len(brain_files)} files\n{push}"

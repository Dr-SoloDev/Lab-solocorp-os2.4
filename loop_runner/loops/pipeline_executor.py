import shutil
import subprocess
from datetime import timedelta
from pathlib import Path

from ..runner import Loop

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from central_bus import queue, state

import os
PROJECT_PATHS = {
    "bangkok-pos": os.environ.get("BKK_POS_PATH", "/tmp/bangkok-pos"),
}

AGENT_PERSONA = {
    "engineering": "คุณคือ ช่างฟูล (Head of Engineering) ของ SoloCorp — full-stack developer",
    "ui_designer": "คุณคือ UI Designer ของ SoloCorp — สร้าง component และ wireframe",
    "qa":          "คุณคือ QA ทีม ของ SoloCorp — ทดสอบและรายงาน bug",
    "design":      "คุณคือ ครีเอท (Creative Director) ของ SoloCorp — ออกแบบ UI/UX",
    "product":     "คุณคือ โปรดัค (Product Manager) ของ SoloCorp — เขียน PRD และ spec",
}

# Map department → Hermes model_alias (from config.yaml)
# Used when routing via Hermes; falls back to Claude CLI if hermes unavailable
AGENT_MODEL = {
    "engineering": "deepseek-v4-pro",
    "ui_designer": "deepseek-v4-flash",
    "qa":          "deepseek-v4-flash",
    "design":      "deepseek-v4-flash",
    "product":     "deepseek-v4-flash",
}

MAX_TASKS_PER_RUN = 2  # conservative — each task may take minutes


class PipelineExecutorLoop(Loop):
    loop_id = "pipeline_executor"
    interval = timedelta(minutes=30)
    trust_level = 4  # L4 — auto-execute without approval
    model_hint = "glm-5.2"  # cron scheduler sub-agent; individual tasks use AGENT_MODEL per dept

    def run(self) -> str:
        executed = []
        for priority in ("high", "normal"):
            while len(executed) < MAX_TASKS_PER_RUN:
                msg = queue.dequeue(priority)
                if not msg:
                    break
                # skip non-task messages (HANDOFF, GOVERNANCE, etc.)
                if getattr(msg, 'type', '') != 'task':
                    continue
                desc = msg.payload.get("description", "").strip()
                if not desc:
                    continue
                result = self._dispatch(msg)
                executed.append(f"[{msg.to_dept}] {msg.payload.get('task_id', '?')}: {result[:120]}")

        if not executed:
            return "⏭ pipeline_executor: queue empty — nothing to run"
        return "✅ pipeline_executor ran " + str(len(executed)) + " tasks:\n" + "\n".join(executed)

    def _dispatch(self, msg) -> str:
        persona = AGENT_PERSONA.get(msg.to_dept, f"คุณคือ {msg.to_dept} agent ของ SoloCorp")
        model_alias = AGENT_MODEL.get(msg.to_dept, "deepseek-v4-flash")
        proj_path = PROJECT_PATHS.get(msg.project_id)
        task_id = msg.payload.get("task_id", "")
        desc = msg.payload.get("description", "")

        prompt = (
            f"{persona}\n\n"
            f"Project: {msg.project_id}\n"
            f"Task {task_id}: {desc}\n\n"
            f"ทำ task นี้ให้เสร็จสมบูรณ์ รายงานผลเมื่อเสร็จ"
        )

        # Try Hermes first (routes through department's assigned model),
        # fallback to Claude CLI
        # Resolve CLI paths — nvm/pyenv may not be in subprocess PATH
        hermes = shutil.which("hermes")
        claude = shutil.which("claude") or "/home/drsolodev/.nvm/versions/node/v24.14.1/bin/claude"

        output = None
        if hermes:
            r = subprocess.run(
                [hermes, "chat", "-q", prompt, "-Q", "--yolo",
                 "-m", model_alias],
                capture_output=True, text=True, timeout=300,
                cwd=proj_path,
            )
            raw = (r.stdout or r.stderr or "").strip()
            if r.returncode == 0 and not raw.startswith("Error:"):
                output = raw

        if output is None and Path(claude).exists():
            r = subprocess.run(
                [claude, "--dangerously-skip-permissions", "-p", prompt],
                capture_output=True, text=True, timeout=120,
                cwd=proj_path,
            )
            output = (r.stdout or r.stderr or "no output").strip()

        if output is None:
            output = f"ERROR: no CLI runner available (hermes={hermes}, claude={claude})"

        # Persist artifact
        artifact_dir = (
            Path(__file__).parent.parent.parent
            / "bus" / "projects" / msg.project_id / "artifacts"
        )
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / f"{msg.trace_id}.txt").write_text(output)

        return output

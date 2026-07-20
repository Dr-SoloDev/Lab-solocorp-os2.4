"""
👑 Owner Dashboard — SoloCorp OS
มองปราดเดียวรู้เรื่อง: สถานะระบบ + active tasks + blockers + summary

Legacy API (backward compat):
    summary(project_id) → dict
    all_projects() → list[dict]
    render(project_id) → str

New API:
    owner_dashboard(format="markdown") → str
    owner_dashboard(format="json") → dict

API:
    GET /v1/dashboard  → JSON
    GET /v1/dashboard?format=markdown  → Markdown
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Backward Compat: keep old functions ───────────────────────────────
STATUS_ICON = {"pending": "⏳", "in_progress": "🔄", "done": "✅", "failed": "❌"}

def summary(project_id: str) -> dict:
    from central_bus.state import get
    state = get(project_id)
    phases = state["phases"]
    done = sum(1 for p in phases.values() if p["status"] == "done")
    total = len(phases)
    return {
        "project_id": project_id,
        "name": state.get("name", ""),
        "status": state["status"],
        "phase": state["phase"],
        "progress_pct": round(done / total * 100),
        "phases": {k: v["status"] for k, v in phases.items()},
        "blockers": state.get("blockers", []),
    }

def all_projects() -> list[dict]:
    from central_bus.state import PROJECTS_DIR
    if not PROJECTS_DIR.exists():
        return []
    return [summary(p.name) for p in sorted(PROJECTS_DIR.iterdir()) if p.is_dir()]

def render(project_id: str) -> str:
    s = summary(project_id)
    lines = [
        f"## Pipeline: {s['name'] or project_id}",
        f"Status: {s['status']} | Phase: {s['phase']} | Progress: {s['progress_pct']}%",
        "",
        "### Phases",
    ]
    for phase, status in s["phases"].items():
        lines.append(f"  {STATUS_ICON.get(status,'?')} {phase}: {status}")
    if s["blockers"]:
        lines.append("\n### Blockers")
        lines.extend(f"  - {b}" for b in s["blockers"])
    return "\n".join(lines)


# ── Paths ──────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
BUS_DISPATCH = BASE / "bus/dispatch"
BUS_QUEUE = BASE / "bus/queue"
BUS_EVIDENCE = BASE / "bus/evidence"
BRAIN_DIR = BASE / "brain"
PROFILES_DIR = BASE / "profiles"

# ── RAG Status ─────────────────────────────────────────────────────────
def _rag(value: float) -> str:
    if value >= 90: return "🟢"
    if value >= 70: return "🟡"
    return "🔴"


def _latest_dispatch_dir() -> Path | None:
    """Find the most recent dispatch directory."""
    if not BUS_DISPATCH.exists():
        return None
    dates = sorted(BUS_DISPATCH.iterdir(), reverse=True)
    return dates[0] if dates else None


def _count_dispatches() -> dict:
    """Count dispatches by priority."""
    counts = {"P0": 0, "P1": 0, "P2": 0, "total": 0}
    if not BUS_DISPATCH.exists():
        return counts
    for date_dir in BUS_DISPATCH.iterdir():
        if not date_dir.is_dir():
            continue
        for f in date_dir.iterdir():
            if f.suffix != ".json":
                continue
            counts["total"] += 1
            try:
                data = json.loads(f.read_text())
                pri = data.get("command", data).get("priority", "P2")
                if pri in counts:
                    counts[pri] += 1
            except (json.JSONDecodeError, KeyError):
                pass
    return counts


def _queue_depth() -> dict:
    """Read queue depths."""
    q = {"high": 0, "normal": 0, "dead": 0}
    try:
        if (BUS_QUEUE / "high.jsonl").exists():
            q["high"] = len((BUS_QUEUE / "high.jsonl").read_text().splitlines())
        if (BUS_QUEUE / "normal.jsonl").exists():
            q["normal"] = len((BUS_QUEUE / "normal.jsonl").read_text().splitlines())
        dl = BUS_QUEUE / "dead_letter"
        if dl.exists():
            q["dead"] = len(list(dl.iterdir())) if dl.is_dir() else 0
    except Exception:
        pass
    return q


def _evidence_count() -> int:
    if not BUS_EVIDENCE.exists():
        return 0
    return len([f for f in BUS_EVIDENCE.iterdir() if f.suffix == ".json"])


def _git_status() -> dict:
    try:
        r = subprocess.run(
            ["git", "-C", str(BASE), "log", "--oneline", "-1"],
            capture_output=True, text=True, timeout=5
        )
        last_commit = r.stdout.strip()
        r2 = subprocess.run(
            ["git", "-C", str(BASE), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        dirty = len([l for l in r2.stdout.splitlines() if l.strip()])
        return {"last_commit": last_commit, "dirty_files": dirty}
    except Exception:
        return {"last_commit": "unknown", "dirty_files": 0}


def _active_dispatches() -> list[dict]:
    """Get today's dispatches."""
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = BUS_DISPATCH / today
    if not today_dir.exists():
        return []
    dispatches = []
    for f in sorted(today_dir.iterdir()):
        if f.suffix != ".json":
            continue
        try:
            data = json.loads(f.read_text())
            cmd = data.get("command", data)
            dispatches.append({
                "id": cmd.get("id", f.stem),
                "to": cmd.get("to", "unknown"),
                "priority": cmd.get("priority", "P2"),
                "title": cmd.get("title", cmd.get("name", "")),
                "deadline": cmd.get("deadline", ""),
            })
        except json.JSONDecodeError:
            pass
    return dispatches


def _brain_stats() -> dict:
    """Count brain files."""
    if not BRAIN_DIR.exists():
        return {"files": 0}
    return {"files": len([f for f in BRAIN_DIR.iterdir() if f.suffix in (".md", ".json")])}


def _profile_count() -> int:
    if not PROFILES_DIR.exists():
        return 0
    return len([d for d in PROFILES_DIR.iterdir() if d.is_dir() and d.name[0].isdigit()])


def owner_dashboard(format: str = "markdown") -> str | dict:
    """Generate Owner Dashboard — one-glance view."""
    disp = _count_dispatches()
    queue = _queue_depth()
    git = _git_status()
    active = _active_dispatches()
    brain = _brain_stats()
    evidence = _evidence_count()
    profiles = _profile_count()

    # ── Compute RAG scores ───────────────────────────────────────────
    # System health score (0-100)
    score = 100
    if queue["dead"] > 0: score -= 10
    if git["dirty_files"] > 0: score -= min(git["dirty_files"] * 2, 20)
    if disp.get("P0", 0) > 0: score -= 15
    # Central Bus health — check if process is running
    try:
        r = subprocess.run(
            ["pgrep", "-f", "central_bus.main"],
            capture_output=True, text=True, timeout=3
        )
        if not r.stdout.strip():
            score -= 30
    except Exception:
        pass

    rag = _rag(score)

    # ── Build response ────────────────────────────────────────────────
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if format == "json":
        return {
            "timestamp": now,
            "health": {"score": score, "rag": rag},
            "git": git,
            "dispatches": disp,
            "queue": queue,
            "evidence": evidence,
            "active_dispatches": active,
            "brain": brain,
            "profiles": profiles,
        }

    # Markdown output
    lines = [
        f"# 👑 SoloCorp OS — Owner Dashboard",
        f"> {now} | Health: {rag} {score}/100",
        "",
    ]

    # ── Active Commands ──────────────────────────────────────────────
    if active:
        lines.append("## 📨 Active Dispatches (Today)")
        for a in active:
            pri_icon = {"P0": "🔴", "P1": "🟡", "P2": "🟢", "P3": "⚪"}.get(a["priority"], "⚪")
            deadline = f" ⏰ {a['deadline']}" if a["deadline"] else ""
            lines.append(f"  {pri_icon} **{a['id']}** → {a['to']}: {a['title']}{deadline}")
        lines.append("")

    # ─── System Metrics Row ─────────────────────────────────────────
    lines.append("## 📊 System Metrics")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|:-------|:-----:|")
    lines.append(f"| Git | `{git['last_commit']}` |")
    lines.append(f"| Dirty Files | {git['dirty_files']} |")
    lines.append(f"| Active Dispatches | {disp['total']} (P0:{disp['P0']} P1:{disp['P1']}) |")
    lines.append(f"| Queue Depth | High:{queue['high']} Normal:{queue['normal']} Dead:{queue['dead']} |")
    lines.append(f"| Evidence Records | {evidence} |")
    lines.append(f"| Brain Files | {brain['files']} |")
    lines.append(f"| Active Profiles | {profiles} |")
    lines.append("")

    # ─── Quick Actions ──────────────────────────────────────────────
    lines.append("## 🎯 Quick Actions")
    lines.append("")
    lines.append(f"| Action | Command |")
    lines.append(f"|:-------|:--------|")
    lines.append(f"| Full Status | `/status` |")
    lines.append(f"| Audit | `/audit` |")
    lines.append(f"| Deploy | `/deploy` |")
    lines.append(f"| Pipeline | `/pipeline <feature>` |")
    lines.append(f"| Brain | `/brain <context>` |")
    lines.append("")
    lines.append("---")
    lines.append("*Dashboard auto-generated | SoloCorp OS*")

    return "\n".join(lines)

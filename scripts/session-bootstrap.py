#!/usr/bin/env python3
"""
🔄 Auto-Session Bootstrap — SoloCorp OS
Context injection auto ตอนเริ่ม session
Output: concise markdown of current state

Usage:
    python scripts/session-bootstrap.py          # markdown (default)
    python scripts/session-bootstrap.py --json   # JSON

Notes:
    - ทุก text I/O ระบุ encoding="utf-8" ชัดเจน (Windows default เป็น cp874)
    - ไฟล์ที่อ่านไม่ได้/เสีย → ข้าม + รายงานใน warnings ไม่ทำให้ bootstrap ล้ม
"""

import json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
BRAIN_DIR = BASE / "brain"
DISPATCH_DIR = BASE / "bus/dispatch"
QUEUE_DIR = BASE / "bus/queue"
CANONICAL_VENV = Path("/data/projects/Lab-solocorp-os2.4/.venv")
CANONICAL_PY = CANONICAL_VENV / "bin/python3"

# Collected non-fatal problems, surfaced in the output instead of crashing.
WARNINGS: list[str] = []


def _warn(msg: str) -> None:
    WARNINGS.append(msg)


def _git(cmd: list[str]) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(BASE)] + cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        _warn(f"git {' '.join(cmd)} failed: {exc}")
        return ""
    return r.stdout.strip()


def _is_linked_worktree() -> bool:
    """linked worktree = git-dir ≠ git-common-dir (main checkout: both .git)."""
    git_dir = _git(["rev-parse", "--absolute-git-dir"])
    common_dir = _git(["rev-parse", "--git-common-dir"])
    if not git_dir or not common_dir:
        return False
    try:
        return Path(git_dir).resolve() != (BASE / common_dir).resolve()
    except OSError:
        return git_dir != common_dir


def _rag(v: float) -> str:
    if v >= 90:
        return "🟢"
    if v >= 70:
        return "🟡"
    return "🔴"


# --- session-log.md parsing ------------------------------------------------
# Real formats found in brain/session-log.md:
#   1. "## 2026-07-27 07:35 — API Key Protection Team Rollout ✅"
#   2. "## Session Auto-Summary — 2026-11-02 19:19 UTC"
#   3. legacy "## Session #12 — title" / "## Session #12"
#   4. legacy Thai dates, e.g. "## 13 ส.ค. 2569 — …" (kept as title only)
# The log is append-only, so the LAST heading in file order is the latest session.

_HEADING_RE = re.compile(r"^##[ \t]+(?P<heading>[^\n]+?)[ \t]*$", re.M)
_SEP = r"[\u2014\u2013\u2012\u2015\-\u00b7:]"  # em/en/figure/horizontal dash, hyphen, middot, colon
_ISO_DT_RE = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})"
    r"(?:[ T]+(?P<time>\d{1,2}:\d{2}))?"
    r"(?:[ \t]*(?P<tz>UTC|Z|[+-]\d{2}:?\d{2}))?"
)
_LEGACY_NUM_RE = re.compile(
    r"^Session\s*#\s*(?P<num>\d+)\b(?:[ \t]*" + _SEP + r")?[ \t]*(?P<rest>.*)$",
    re.IGNORECASE,
)


def _strip_separators(text: str) -> str:
    """Trim leading/trailing dash-like separators and collapse whitespace."""
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    text = re.sub(r"^" + _SEP + r"+\s*", "", text)
    text = re.sub(r"\s*" + _SEP + r"+$", "", text)
    return text.strip()


def parse_session_heading(heading: str) -> dict:
    """Parse one level-2 heading into {raw, number, date, time, title}."""
    text = heading.strip().lstrip("#").strip()
    info = {
        "raw": heading.strip(),
        "number": None,
        "date": "",
        "time": "",
        "title": text,
    }

    rest = text
    m = _LEGACY_NUM_RE.match(text)
    if m:
        info["number"] = int(m.group("num"))
        rest = m.group("rest").strip()
        info["title"] = rest or f"Session #{info['number']}"

    m2 = _ISO_DT_RE.search(rest)
    if m2:
        info["date"] = m2.group("date")
        time_part = m2.group("time") or ""
        if m2.group("tz"):
            time_part = f"{time_part} {m2.group('tz')}".strip()
        info["time"] = time_part
        remainder = rest[: m2.start()] + " " + rest[m2.end() :]
        remainder = _strip_separators(remainder)
        if remainder:
            info["title"] = remainder

    return info


def session_label(info: dict) -> str:
    """Human-readable label: '<date> <time> — <title>' (or legacy '#n — title')."""
    head = " ".join(p for p in (info["date"], info["time"]) if p).strip()
    if info["number"] is not None:
        head = " ".join(p for p in (head, f"Session #{info['number']}") if p).strip()
    title = info["title"]
    if title == f"Session #{info['number']}":  # no descriptive title
        title = ""
    parts = [p for p in (head, title) if p]
    return " — ".join(parts) or info["raw"]


def split_sessions(text: str) -> list[dict]:
    """Split the session log into entries keyed by level-2 headings."""
    matches = list(_HEADING_RE.finditer(text))
    entries = []
    for i, m in enumerate(matches):
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        info = parse_session_heading(m.group("heading"))
        info["body"] = text[body_start:body_end]
        info["label"] = session_label(info)
        entries.append(info)
    return entries


def last_session() -> dict:
    """Get most recent session from session-log.md"""
    result = {"session": "?", "count": 0, "summary": "no sessions yet"}
    log = BRAIN_DIR / "session-log.md"
    if not log.exists():
        return result
    try:
        text = log.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _warn(f"brain/session-log.md unreadable: {exc}")
        result["summary"] = "session log unreadable"
        return result

    entries = split_sessions(text)
    if not entries:
        return result

    latest = entries[-1]
    lines = latest["body"].splitlines()
    summary: dict = {
        "session": latest["label"],
        "count": len(entries),
        "date": latest["date"],
        "time": latest["time"],
        "title": latest["title"],
        "number": latest["number"],
    }
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("**Summary:**"):
            summary["summary"] = stripped.split("**Summary:**", 1)[1].strip()
        if "**Mode:**" in line:
            summary["mode"] = line.split("**Mode:**", 1)[1].strip()
        if stripped.startswith("### Key Decisions"):
            decisions = []
            for j in range(i + 1, min(i + 20, len(lines))):
                row = lines[j].strip()
                if not row.startswith("|"):
                    if row:
                        break
                    continue
                parts = [p.strip() for p in row.split("|")]
                if len(parts) >= 4 and parts[1].isdigit():
                    decisions.append(parts[2])
            if decisions:
                summary["decisions"] = decisions
            break

    # Auto-Summary entries carry no **Summary:** line — fall back to the title.
    summary.setdefault("summary", summary.get("title") or latest["label"])
    return summary


def active_dispatches() -> list[dict]:
    """Find ongoing dispatches"""
    active = []
    if not DISPATCH_DIR.exists():
        return active
    for date_dir in sorted(DISPATCH_DIR.iterdir(), reverse=True)[:3]:
        if not date_dir.is_dir():
            continue
        for f in sorted(date_dir.iterdir())[:10]:
            if f.suffix != ".json":
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                _warn(
                    f"skip dispatch {date_dir.name}/{f.name}: {exc.__class__.__name__}"
                )
                continue
            status = data.get(
                "status", data.get("command", {}).get("status", "unknown")
            )
            if status in ("pending", "in_progress", "assigned"):
                active.append(
                    {
                        "id": f.stem,
                        "date": date_dir.name,
                        "status": status,
                        "summary": data.get(
                            "summary", data.get("command", {}).get("description", "")
                        ),
                        "priority": data.get("command", {}).get("priority", "P2"),
                    }
                )
    return active


def queue_depth() -> dict:
    """Check queue length"""
    counts = {"high": 0, "normal": 0, "dead": 0}
    if not QUEUE_DIR.exists():
        return counts
    for qfile in QUEUE_DIR.iterdir():
        if qfile.suffix == ".offset":
            continue
        name = qfile.stem
        if name in counts:
            try:
                lines = qfile.read_text(encoding="utf-8").strip().split("\n")
                counts[name] = len([l for l in lines if l.strip()])
            except (OSError, UnicodeDecodeError) as exc:
                _warn(f"skip queue {qfile.name}: {exc.__class__.__name__}")
    return counts


def pending_from_brain() -> list[str]:
    """Extract pending_next from ceo-memory.json"""
    mem = BRAIN_DIR / "ceo-memory.json"
    if not mem.exists():
        return []
    try:
        data = json.loads(mem.read_text(encoding="utf-8"))
        sessions = data.get("sessions", [])
        if sessions:
            last = sessions[-1]
            return last.get("pending_next", [])
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        KeyError,
        IndexError,
    ) as exc:
        _warn(f"brain/ceo-memory.json unreadable: {exc.__class__.__name__}")
    return []


def system_health() -> dict:
    """Quick health check of key paths"""
    paths = {
        "bus/": BASE / "bus",
        "central_bus/": BASE / "central_bus",
        "rules/": BASE / "rules",
        "sop/": BASE / "sop",
        "profiles/": BASE / "profiles",
        "workers/": BASE / "workers",
    }
    healthy = all(p.exists() for p in paths.values())
    return {"healthy": healthy, "paths": {k: v.exists() for k, v in paths.items()}}


def preflight_venv() -> dict:
    """Check .venv — Worktree MCP Contract (plan A)."""
    venv = BASE / ".venv"
    py = venv / "bin/python3"
    linked = _is_linked_worktree()
    if not venv.exists() and not venv.is_symlink():
        fix = (
            f"ln -s {CANONICAL_VENV} {venv}  หรือ  bash scripts/worktree-setup.sh --fix-only"
            if linked
            else f"python3 -m venv {venv}"
        )
        return {
            "ok": False,
            "status": "missing",
            "detail": f"{venv} ไม่มี — MCP spawn จะ NotFound",
            "fix": fix,
        }
    if venv.is_symlink() and linked:
        target = (
            venv.resolve()
            if venv.exists()
            else Path(venv.readlink() if hasattr(venv, "readlink") else "")
        )
        # readlink fallback
        try:
            link_target = Path(venv.readlink()) if hasattr(venv, "readlink") else target
        except Exception:
            link_target = target
        # check raw link text
        try:
            raw = str((BASE / ".venv").readlink())
        except Exception:
            raw = str(target)
        if raw != str(CANONICAL_VENV) and str(target) != str(CANONICAL_VENV):
            # allow if resolves to canonical
            if target != CANONICAL_VENV:
                return {
                    "ok": False,
                    "status": "wrong_target",
                    "detail": f".venv symlink ชี้ไป {raw} (resolve {target}) ไม่ใช่ {CANONICAL_VENV}",
                    "fix": f"ln -snf {CANONICAL_VENV} {venv}",
                }
    if not py.exists():
        return {
            "ok": False,
            "status": "broken",
            "detail": f"{py} ไม่มี/h execute ไม่ได้ — venv ชี้ผิดหรือ canonical หาย",
            "fix": f"ls -la {venv} && ls -la {CANONICAL_VENV}/bin/python3",
        }
    # real directory: valid in main checkout; linked worktree must use symlink
    if venv.is_dir() and not venv.is_symlink():
        if not linked:
            return {
                "ok": True,
                "status": "ok_real_dir",
                "detail": f"{venv} เป็น directory จริงในโฟลเดอร์หลัก — ใช้ได้",
                "fix": "",
            }
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        bak = f"{venv}.bak-{ts}"
        return {
            "ok": False,
            "status": "not_symlink",
            "detail": ".venv เป็น directory จริงใน linked worktree — เปลือง disk + ไม่ตาม contract",
            "fix": f"mv {venv} {bak} && ln -s {CANONICAL_VENV} {venv}",
        }
    return {
        "ok": True,
        "status": "ok",
        "detail": f".venv -> {CANONICAL_VENV}"
        if linked
        else f"{venv} (main checkout) ใช้ได้",
        "fix": "",
    }


def preflight_mcp_config() -> dict:
    """Check opencode.json(c) ไม่มี relative .venv/bin/python3 เหลือ."""
    issues: list[str] = []
    for fname in ("opencode.json", "opencode.jsonc"):
        p = BASE / fname
        if not p.exists():
            continue
        try:
            text = p.read_text()
        except Exception as e:
            issues.append(f"{fname}: อ่านไม่ได้ ({e})")
            continue
        # relative pattern: ".venv/bin/python3" quoted
        if '".venv/bin/python3"' in text or "' .venv" in text:
            issues.append(
                f'{fname}: มี \'".venv/bin/python3"\' แบบ relative — ต้องเป็น "{CANONICAL_PY}"'
            )
        # catch any bare .venv in command without absolute prefix
        # count lines with command containing .venv but not canonical
        for i, line in enumerate(text.splitlines(), 1):
            if ".venv/bin/python3" in line and str(CANONICAL_VENV) not in line:
                # allow stealth-browser venv (tools/.../venv) — not counted
                if "tools/stealth-browser-mcp" in line:
                    continue
                issues.append(f"{fname}:{i}: relative .venv → {line.strip()[:90]}")
                break
    if issues:
        return {
            "ok": False,
            "status": "relative_found",
            "detail": "; ".join(issues[:3]),
            "fix": f"แก้ {CANONICAL_PY} ให้เป็น absolute ทุกจุด — ดู docs/runbooks/WORKTREE-MCP-CONTRACT.md §4",
        }
    return {
        "ok": True,
        "status": "ok",
        "detail": "opencode.json(c) absolute OK",
        "fix": "",
    }


def preflight_all() -> dict:
    v = preflight_venv()
    c = preflight_mcp_config()
    ok = v["ok"] and c["ok"]
    return {"ok": ok, "venv": v, "mcp_config": c}


def bootstrap() -> dict:
    """Generate complete bootstrap context"""
    WARNINGS.clear()
    health = system_health()
    q = queue_depth()
    disp = active_dispatches()
    ses = last_session()
    pending = pending_from_brain()
    preflight = preflight_all()

    # Calculate health score
    score = 100
    if not health["healthy"]:
        score -= 25
    if len(disp) > 5:
        score -= 10
    if q["dead"] > 0:
        score -= 15
    if not pending:
        score += 5  # No backlog = good
    if not preflight["ok"]:
        score -= 30  # MCP pre-flight fail = red

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "health": {
            "score": min(100, max(0, score)),
            "rag": _rag(score),
            "systems": health["paths"],
        },
        "preflight": preflight,
        "git": {
            "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
            "last_commit": _git(["log", "-1", "--oneline"]),
            "dirty": bool(_git(["status", "--porcelain"])),
        },
        "brain": {
            "last_session": ses.get("session", "?"),
            "session_count": ses.get("count", 0),
            "last_session_date": ses.get("date", ""),
            "last_session_time": ses.get("time", ""),
            "last_summary": ses.get("summary", ""),
            "last_mode": ses.get("mode", ""),
            "pending_items": pending,
        },
        "work": {
            "active_dispatches": disp,
            "queue": q,
        },
        "warnings": list(WARNINGS),
        "reminder": "เปิด rules/INDEX.md เมื่อไม่แน่ใจ behavior — แต่ละพฤติกรรมจบใน 1 ไฟล์",
    }


def format_markdown(data: dict) -> str:
    lines = [
        f"# 🔄 Auto Bootstrap — SoloCorp OS ({data['generated_at']})",
        "",
        f"## 🏥 Health: {data['health']['rag']} {data['health']['score']}/100",
        "",
    ]
    # Systems
    ok = [k for k, v in data["health"]["systems"].items() if v]
    fail = [k for k, v in data["health"]["systems"].items() if not v]
    if ok:
        lines.append(f"  ✅ {', '.join(ok)}")
    if fail:
        lines.append(f"  ❌ {', '.join(fail)}")
    # Pre-flight — Worktree MCP Contract
    pf = data.get("preflight")
    if pf is not None:
        if pf["ok"]:
            lines.append(f"  ✅ MCP pre-flight: venv OK + config absolute OK")
        else:
            lines.append(f"  🔴 MCP PRE-FLIGHT FAIL")
            for key in ("venv", "mcp_config"):
                part = pf.get(key, {})
                if not part.get("ok"):
                    lines.append(f"    🔴 {key}: {part.get('detail', '')}")
                    if part.get("fix"):
                        lines.append(f"       ↳ fix: {part.get('fix')}")
            lines.append(f"  📖 docs/runbooks/WORKTREE-MCP-CONTRACT.md §4")
    lines += ["", f"## 📦 Git: {data['git']['branch']} — {data['git']['last_commit']}"]
    if data["git"]["dirty"]:
        lines.append("  ⚠️ dirty — มี uncommitted changes")
    lines += ["", "## 🧠 Brain"]
    count = data["brain"].get("session_count", 0)
    suffix = f" (จากทั้งหมด {count} session)" if count else ""
    lines.append(f"  Session: {data['brain']['last_session']}{suffix}")
    if data["brain"]["last_summary"]:
        lines.append(f"  Summary: {data['brain']['last_summary']}")
    if data["brain"]["last_mode"]:
        lines.append(f"  Mode: {data['brain']['last_mode']}")
    if data["brain"]["pending_items"]:
        lines.append("  📌 Pending:")
        lines.extend(f"    - {item}" for item in data["brain"]["pending_items"])
    lines += ["", "## 📋 Active Work"]
    q = data["work"]["queue"]
    lines.append(f"  Queue: high={q['high']} normal={q['normal']} dead={q['dead']}")
    disp = data["work"]["active_dispatches"]
    if disp:
        lines.append(f"  Active dispatches ({len(disp)}):")
        for d in disp[:5]:
            icon = {"P0": "🔴", "P1": "🟡", "P2": "🟢", "P3": "⚪"}.get(
                d["priority"], "⚪"
            )
            lines.append(f"    {icon} [{d['priority']}] {d['summary'][:80]}")
    else:
        lines.append("  No active dispatches")
    if data.get("warnings"):
        lines += ["", "## ⚠️ Warnings (ข้ามไฟล์ที่อ่านไม่ได้)"]
        lines.extend(f"  - {w}" for w in data["warnings"])
    lines += ["", "---", f"💡 {data['reminder']}"]
    return "\n".join(lines)


if __name__ == "__main__":
    # Windows console defaults to cp874 — make printing Thai/emoji safe.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass
    data = bootstrap()
    # exit code: 0 = ok, 2 = pre-flight fail (red — not green)
    exit_code = 0
    pf = data.get("preflight")
    if pf is not None and not pf["ok"]:
        exit_code = 2
        # honor --json but still exit 2
    if "--json" in sys.argv:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(format_markdown(data))
    if "--no-preflight-check" in sys.argv:
        sys.exit(0)
    sys.exit(exit_code)

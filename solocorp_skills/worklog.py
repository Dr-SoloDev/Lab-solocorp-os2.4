"""Work Log Miner — ขุด "เรื่องราวของเรา" ออกจากงานจริงใน repo

ทำไมต้องมี: สนามแรกเปลี่ยนจาก "ช่วยครีเอเตอร์อื่น" เป็น
**"SoloCorp เป็นครีเอเตอร์ตัวแรกของตัวเอง"** (Owner 2026-10-20)
เนื้อหาจึงไม่ต้องคิดขึ้นเอง — มันคือ **สิ่งที่เราทำจริงอยู่แล้ว**
เขียนในรูป "เจอปัญหาอะไร · แก้อะไร · เพื่ออะไร" = ประวัติการทำงาน
ที่กลายเป็นเรซูเม่ของคนสร้างตัวตน

แหล่งข้อมูล (ทั้งหมดอยู่ใน repo แล้ว):
  1. ``decisions/ADR-*.md``   — ปัญหา → การตัดสินใจ → เหตุผล
  2. ``brain/session-log.md`` — งานรายวัน
  3. ``git log``              — commit ที่แก้ปัญหาจริง
  4. ``bus/evidence/*.json``  — เคสที่พังแล้วแก้ (expected/actual จริง)

ข้อห้ามที่ยึด (จาก vision §5.2 + §6):
  • เรื่องต้องมี **รอยแผลจริง** ไม่ใช่แค่ผลงาน
  • ต้องตอบได้ว่า **"เพื่ออะไร"**
  • ห้ามขายฝันยอดขาย/ผู้ติดตาม
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

__all__ = [
    "WorkStory",
    "collect_stories",
    "story_to_idea",
    "build_text_post",
    "ROOT",
]

ROOT = Path(__file__).resolve().parent.parent
DECISIONS_DIR = ROOT / "decisions"
SESSION_LOG = ROOT / "brain" / "session-log.md"
EVIDENCE_DIR = ROOT / "bus" / "evidence"


@dataclass
class WorkStory:
    """เรื่องราว 1 เรื่อง ที่ยกมาจากงานจริง"""
    kind: str                  # adr | commit | session | evidence
    ref: str                   # ที่อ้างอิง (ไฟล์ / commit / วันที่)
    title: str                 # หัวข้อ
    problem: str = ""          # เจอปัญหาอะไร
    fix: str = ""              # แก้อะไร
    why: str = ""              # เพื่ออะไร
    evidence: str = ""         # หลักฐาน / ตัวเลข
    date: str = ""
    score: int = 0             # คะแนนความ "เล่าได้ดี"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "ref": self.ref, "title": self.title,
            "problem": self.problem, "fix": self.fix, "why": self.why,
            "evidence": self.evidence, "date": self.date, "score": self.score,
        }


# ══════════════════════════════════════════════════════════════════════
# ขุดจาก ADR
# ══════════════════════════════════════════════════════════════════════


def _md_section(text: str, heading: str) -> str:
    """ดึงเนื้อหาใต้หัวข้อระดับ 2 (## heading)"""
    pattern = rf"^##\s+{re.escape(heading)}\s*$"
    m = re.search(pattern, text, re.M | re.I)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"^##\s+", rest, re.M)
    return (rest[:nxt.start()] if nxt else rest).strip()


def _clean_md(text: str, max_chars: int = 700) -> str:
    """ทำความสะอาดของ markdown ให้เหลือเนื้อความอ่านได้"""
    if not text:
        return ""
    t = re.sub(r"^#{1,6}\s+.*$", "", text, flags=re.M)   # หัวข้อย่อย
    t = re.sub(r"```.*?```", "", t, flags=re.S)            # code block
    t = re.sub(r"`([^`]+)`", r"\1", t)                     # inline code
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)               # bold
    t = re.sub(r"^\s*[-*+]\s+", "", t, flags=re.M)         # bullet
    t = re.sub(r"^\s*\|.*$", "", t, flags=re.M)            # table
    t = re.sub(r"\n{2,}", "\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()[:max_chars]


def _from_adr(path: Path) -> Optional[WorkStory]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None

    title_m = re.search(r"^#\s+(.+)$", text, re.M)
    title = title_m.group(1).strip() if title_m else path.stem

    problem = _clean_md(_md_section(text, "บริบท") or _md_section(text, "Context"))
    decision = _clean_md(_md_section(text, "การตัดสินใจ") or _md_section(text, "Decision"))
    impact = _clean_md(_md_section(text, "ผลกระทบ") or _md_section(text, "Consequences"))

    # ADR ที่ยังไม่ตัดสินใจ → ยังไม่ใช่เรื่องที่ "เล่าได้"
    if not decision:
        return None

    # เหตุผล = บรรทัดแรกของผลกระทบที่พูดถึงเหตุผล/ข้อดี
    why = ""
    for line in impact.splitlines():
        line = line.strip(" -•*")
        if len(line) > 40 and not line.startswith(("http", "❌", "⚠️", "🔴")):
            why = line
            break

    score = 0
    if problem:
        score += 3
    if why:
        score += 2
    if re.search(r"(พัง|ตาย|โกหก|ค้าง|ผิด|bug|error|ล้ม|หาย|เสีย)", problem + decision, re.I):
        score += 3   # มีรอยแผลจริง

    date_m = re.search(r"\*\*วันที่\*\*:\s*(\d{4}-\d{2}-\d{2})", text)
    return WorkStory(
        kind="adr", ref=path.name, title=title,
        problem=problem, fix=decision, why=why,
        evidence=f"decisions/{path.name}",
        date=date_m.group(1) if date_m else "",
        score=score,
    )


# ══════════════════════════════════════════════════════════════════════
# ขุดจาก session log
# ══════════════════════════════════════════════════════════════════════


def _from_session_log(path: Path) -> list[WorkStory]:
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []

    stories: list[WorkStory] = []
    # ## 2026-07-27 07:35 — หัวข้อ
    heads = list(re.finditer(r"^##\s+(\d{4}-\d{2}-\d{2})[^\n—]*—\s*(.+)$", text, re.M))
    for i, m in enumerate(heads):
        body = text[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        req = re.search(r"\*\*Owner Request:\*\*\s*(.+)", body)
        mission = re.search(r"###\s*🎯\s*Mission Accomplished\s*(.+?)(?=\n---|\n###|\Z)", body, re.S)
        built = re.search(r"###\s*📊\s*What Was Built\s*(.+?)(?=\n---|\n###|\Z)", body, re.S)

        why = _clean_md(req.group(1), 300) if req else ""
        fix = _clean_md(mission.group(1), 400) if mission else (
            _clean_md(built.group(1), 400) if built else "")
        if not fix and not why:
            continue
        stories.append(WorkStory(
            kind="session", ref=f"brain/session-log.md#{m.group(1)}",
            title=m.group(2).strip(),
            problem=why, fix=fix, why="",
            evidence=f"วันที่ {m.group(1)}",
            date=m.group(1),
            score=3 + (2 if why else 0),
        ))
    return stories


# ══════════════════════════════════════════════════════════════════════
# ขุดจาก git log
# ══════════════════════════════════════════════════════════════════════


def _from_git(days: int = 14, limit: int = 60) -> list[WorkStory]:
    try:
        out = subprocess.run(
            ["git", "log", f"-{days*3}", "--format=%H%x1f%ad%x1f%s%x1f%b%x1e",
             "--date=short"],
            capture_output=True, text=True, timeout=30, cwd=str(ROOT),
        ).stdout
    except Exception:
        return []

    stories: list[WorkStory] = []
    for rec in out.split("\x1e"):
        rec = rec.strip("\n")
        if not rec.strip():
            continue
        parts = rec.split("\x1f")
        if len(parts) < 4:
            continue
        sha, date, subject, body = parts[0], parts[1], parts[2], parts[3]
        subject = subject.strip()
        if not subject:
            continue

        # เก็บเฉพาะ commit ที่ "เล่าเรื่องได้" — มี fix/feat และมีรายละเอียด
        if not re.match(r"^(fix|feat|refactor|perf|test|docs|chore)\b", subject, re.I):
            continue
        detail = _clean_md(body, 500)
        if len(detail) < 60:
            continue

        problem = ""
        fix = detail
        why = ""
        for line in detail.splitlines():
            line = line.strip(" -•*")
            if not line:
                continue
            if not problem and re.search(r"(พัง|ตาย|โกหก|ค้าง|ผิด|bug|error|ล้ม|หาย|เสีย|ไม่มี|ไม่ได้)", line, re.I):
                problem = line
                continue
            if not why and re.search(r"(เพราะ|เพื่อ|ทำให้|เลย|เพื่อให้|เพื่อจะ)", line):
                why = line
                break

        score = 2 + (3 if problem else 0) + (2 if why else 0)
        if "chore" in subject.lower() or "docs" in subject.lower():
            score -= 2
        if score < 3:
            continue
        stories.append(WorkStory(
            kind="commit", ref=sha[:8], title=subject,
            problem=problem, fix=fix, why=why,
            evidence=f"git {sha[:8]}",
            date=date, score=score,
        ))
        if len(stories) >= limit:
            break
    return stories


# ══════════════════════════════════════════════════════════════════════
# ขุดจาก evidence (เคสที่พังแล้วแก้ — หลักฐานแข็งที่สุด)
# ══════════════════════════════════════════════════════════════════════


def _from_evidence(limit: int = 30) -> list[WorkStory]:
    if not EVIDENCE_DIR.exists():
        return []
    stories: list[WorkStory] = []
    for p in sorted(EVIDENCE_DIR.glob("*.json"), reverse=True)[:limit]:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        summary = str(d.get("summary", "")).strip()
        if not summary:
            continue
        details = d.get("details") or {}
        problem = str(details.get("problem", "") or details.get("context", ""))
        why = str(details.get("why", "") or details.get("reason", ""))
        score = 4 if d.get("status") == "completed" else 2
        stories.append(WorkStory(
            kind="evidence", ref=p.name, title=summary[:120],
            problem=problem, fix=summary, why=why,
            evidence=f"bus/evidence/{p.name}",
            date=str(d.get("created_at", ""))[:10],
            score=score,
        ))
    return stories


# ══════════════════════════════════════════════════════════════════════
# รวม
# ══════════════════════════════════════════════════════════════════════


def collect_stories(
    *,
    days: int = 14,
    kinds: Optional[tuple[str, ...]] = None,
    limit: int = 40,
    min_score: int = 4,
) -> list[WorkStory]:
    """ขุดเรื่องราวทั้งหมด → เรียงตามคะแนนความเล่าได้"""
    kinds = kinds or ("adr", "commit", "session", "evidence")
    stories: list[WorkStory] = []

    if "adr" in kinds:
        for p in sorted(DECISIONS_DIR.glob("ADR-*.md")) if DECISIONS_DIR.exists() else []:
            s = _from_adr(p)
            if s:
                stories.append(s)

    if "session" in kinds:
        stories.extend(_from_session_log(SESSION_LOG))

    if "commit" in kinds:
        stories.extend(_from_git(days=days))

    if "evidence" in kinds:
        stories.extend(_from_evidence())

    stories = [s for s in stories if s.score >= min_score]
    stories.sort(key=lambda s: (-s.score, s.date), reverse=False)
    stories.sort(key=lambda s: s.score, reverse=True)
    return stories[:limit]


def story_to_idea(story: WorkStory, viewer: str = "") -> dict[str, str]:
    """แปลงเรื่องราว → ไอเดียในรูปแบบ 4 ท่อน (พร้อมส่งให้ LLM ต่อยอด)"""
    problem = story.problem or story.title
    fix = story.fix or ""
    why = story.why or ""
    hook = problem.splitlines()[0][:90] if problem else story.title[:90]
    return {
        "title": story.title[:110],
        "why": why[:200],
        "hook": hook,
        "problem": problem[:600],
        "fix": fix[:800],
        "evidence": story.evidence,
        "source": story.ref,
    }


def build_text_post(
    story: Any,
    *,
    handle: str = "Dr.Solodev",
    tagline: str = "frontier builder / infrastructure for agents",
) -> str:
    """สร้างโพสต์ข้อความสไตล์ "ประกาศเรซูเม่" — เจอปัญหาอะไร แก้อะไร เพื่ออะไร

    รับได้ทั้ง WorkStory และ dict (key: problem/fix/why/evidence)
    """
    if isinstance(story, WorkStory):
        get = lambda k, d="": getattr(story, k, d) or d  # noqa: E731
    else:
        def get(k, d=""):
            v = (story or {}).get(k, d)
            return v if isinstance(v, str) else d

    problem, fix = get("problem"), get("fix")
    why, evidence = get("why"), get("evidence")

    lines = []
    if problem:
        lines.append(f"เจอปัญหา: {problem.splitlines()[0][:180]}")
    if fix:
        lines.append(f"แก้: {fix.splitlines()[0][:200]}")
    if why:
        lines.append(f"เพราะ: {why[:180]}")
    if evidence:
        lines.append(f"หลักฐาน: {evidence}")
    if not lines:
        lines.append(get("title") or "(ไม่มีเนื้อหา)")
    lines.append("")
    lines.append(f"— {handle} · {tagline}")
    return "\n".join(lines)

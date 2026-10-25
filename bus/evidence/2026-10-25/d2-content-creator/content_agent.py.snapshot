"""Content Creator Agent — @content-creator-sek (D2)

เรียกเครื่องมือจริง: read_file / write_file / run_command
+ tool-call log + path guard — ดู docs/certification/D1-content-creator.md
ขอบเขตที่ certify รอบนี้ = LinkedIn social draft เท่านั้น
"""

from __future__ import annotations

import json
import re
import shlex
from datetime import datetime, timezone
from pathlib import Path

from workers.agents.base_agent import BaseAgent

WRITE_ROOT = Path("bus/creative/drafts")
BRAND_SOURCES = (
    "profiles/01-ceo/SOUL.md",
    "profiles/03-cmo/SOUL.md",
    "docs/brand/BRAND-GUIDELINES-v1.md",
)
REQUIRED_SECTIONS = ("## Hook", "## Body", "## CTA", "## Hashtags")
MIN_CHARS, MAX_CHARS = 600, 2500
LOG_PATH = "bus/evidence/2026-10-23/d2-content-creator/tool-calls.jsonl"


class ContentAgent(BaseAgent):
    """Content Creator — Content Production, Caption, Campaign"""

    def __init__(self, bus_url: str = "", api_key: str = "", log_path: str = LOG_PATH):
        super().__init__(
            agent_id="content-creator-sek",
            name="Content เสก",
            profile_path="profiles/15-content-creator/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )
        self.log_path = Path(log_path)
        self.tool_calls: list[dict] = []

    # ── Tool wrapper: log ทุกครั้ง + guard ─────────────────────────────
    def _record(self, tool: str, args, ok: bool) -> None:
        """บันทึก tool call 1 บรรทัด/1 call (append-only)"""
        self.tool_calls.append(
            {"ts": datetime.now(timezone.utc).isoformat(), "tool": tool, "args": args, "ok": ok}
        )
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(self.tool_calls[-1], ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _fail(self, summary: str, error: str, **extra) -> dict:
        return {"status": "failed", "summary": summary,
                "details": {"error": error, "tool_calls": self.tool_calls, **extra}}

    async def _read(self, path: str) -> str:
        text = await self.read_file(path)
        self._record("read_file", path, not text.startswith("❌"))
        return text

    async def _write(self, path: str, content: str) -> str:
        p = Path(path).resolve()
        if not p.is_relative_to(WRITE_ROOT.resolve()):
            raise PermissionError(f"ห้ามเขียนนอก {WRITE_ROOT}: {path}")
        msg = await self.write_file(str(p), content)
        self._record("write_file", str(p), msg.startswith("✅"))
        return msg

    async def _verify(self, path: str) -> dict:
        """ตรวจไฟล์จริงด้วยคำสั่ง (ไม่เชื่อตัวเอง)"""
        cmd = f"test -f {shlex.quote(path)} && wc -m < {shlex.quote(path)}"
        out = await self.run_command(cmd)
        self._record("run_command", cmd, "❌" not in out)
        m = re.search(r"(\d+)", out)
        return {"raw": out, "chars": int(m.group(1)) if m else 0}

    # ── ตัวงาน ────────────────────────────────────────────────────────
    async def execute(self, task: dict) -> dict:
        payload = task.get("payload", {})
        params = payload.get("params", {})
        description = payload.get("description", "")
        brief_path = payload.get("brief_path") or params.get("brief_path")

        if not description and not brief_path:
            return self._fail("ไม่มี description/brief_path", "missing_input")

        # 1) อ่าน brand sources จริง (3 ไฟล์ตาม D1 §5 ข้อ 1)
        sources = {src: await self._read(src) for src in BRAND_SOURCES}

        # 2) อ่าน brief (ไฟล์หรือ description)
        brief = description
        if brief_path:
            brief = await self._read(brief_path)
            if brief.startswith("❌"):
                return self._fail(f"อ่าน brief ไม่ได้: {brief_path}", "brief_unreadable")

        # 3) สร้างเนื้อหา
        content = await self.think(self._build_prompt(brief, sources), max_tokens=2000)
        if not content or content.startswith("⚠️ LLM ไม่พร้อม"):
            return self._fail("LLM ไม่พร้อม — ไม่เขียนไฟล์ (กันข้อมูลปลอม)", "llm_unavailable")

        # 4) ตรวจโครงสร้างก่อนเขียน (fail fast)
        missing = [s for s in REQUIRED_SECTIONS if s not in content]
        if missing:
            return self._fail(f"draft ขาดหัวข้อ: {missing}", "structure_invalid", missing=missing)

        # 5) เขียนจริง + ตรวจด้วยคำสั่ง
        out_path = params.get("out_path") or f"{WRITE_ROOT}/draft-{datetime.now():%Y%m%d-%H%M%S}.md"
        try:
            await self._write(out_path, content)
        except PermissionError as exc:
            return self._fail(str(exc), "write_out_of_bounds")

        check = await self._verify(out_path)
        in_range = MIN_CHARS <= check["chars"] <= MAX_CHARS
        return {
            "status": "completed" if in_range else "failed",
            "summary": f"draft {out_path} ({check['chars']} ตัวอักษร)",
            "details": {
                "agent": self.agent_id,
                "out_path": out_path,
                "chars": check["chars"],
                "in_range": in_range,
                "tool_calls": self.tool_calls,
                "log": str(self.log_path),
            },
        }

    def _build_prompt(self, brief: str, sources: dict) -> str:
        """รวม SOUL + brand guidelines + brief เป็น prompt (ยึด brand voice จริง)"""
        return (
            "คุณคือ Content Creator (เสก) ของ SoloCorp OS\n"
            "เขียน draft โพสต์ LinkedIn ภาษาไทย เป็น markdown ที่มีหัวข้อครบ 4 นี้เท่านั้น:\n"
            "## Hook\n## Body\n## CTA\n## Hashtags\n"
            "ความยาวรวม 700-2000 ตัวอักษร ห้ามใส่คำอธิบายอื่นนอก 4 หัวข้อนี้\n\n"
            f"Brand voice (CEO SOUL): {sources.get('profiles/01-ceo/SOUL.md', '')[:400]}\n"
            f"Marketing direction (CMO SOUL): {sources.get('profiles/03-cmo/SOUL.md', '')[:300]}\n"
            f"Brand guidelines: {sources.get('docs/brand/BRAND-GUIDELINES-v1.md', '')[:400]}\n\n"
            f"BRIEF:\n{brief[:1500]}"
        )

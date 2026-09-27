"""Media Daily — ยิงเจน Flow วันละ 2 ท่อน (เช้า) ตามคิวที่ Owner เคาะแล้ว.

Forum 005 + Owner order (เช้า/2 ท่อน):
- วิ่งวันละครั้งหลัง 06:00 (date-gate — ไม่ดริฟต์แบบ interval)
- ยิงเฉพาะแถว ✅ approved ใน bus/media/queue.md, ไม่เกิน 2 ท่อน/วัน (hard cap)
- flowkit ไม่พร้อม → SKIP + แจ้ง inbox human (ไม่พัง, ไม่เผาเครดิต)
- ทุกครั้งที่ยิง จด bus/media/credits.md; เสีย → inbox __human__
"""
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from ..runner import Loop

import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from workers.flowkit_bridge import is_ready, generate_segment

QUEUE = Path(__file__).parent.parent.parent / "bus" / "media" / "queue.md"
LEDGER = Path(__file__).parent.parent.parent / "bus" / "media" / "credits.md"
MAX_PER_DAY = 2  # hard cap — Owner order (เหลือบัฟเฟอร์ 20/วัน)


class MediaDailyLoop(Loop):
    loop_id = "media_daily"
    interval = timedelta(hours=20)  # fallback; หลักคือ date-gate ข้างล่าง
    trust_level = 4  # L4 auto — แต่มี hard cap 2 ท่อน + ยิงเฉพาะ approved
    model_hint = None  # ไม่ใช้ LLM — ยิง API ตรง (ไม่เผาโทเคน)

    def should_run(self) -> bool:
        try:
            last = datetime.fromisoformat(self.last_run())
            if last.date() >= date.today():
                return False  # วันนี้ยิงแล้ว
        except Exception:
            pass
        return datetime.now().hour >= 6  # เช้าเท่านั้น

    def run(self) -> str:
        ok, why = is_ready()
        if not ok:
            self._alert(f"media_daily SKIP — flowkit ไม่พร้อม: {why}")
            return f"⏭ media_daily: SKIP ({why})"
        due = self._due_segments()
        if not due:
            return "⏭ media_daily: ไม่มีท่อน approved รอยิง"
        fired = []
        for seg in due[:MAX_PER_DAY]:
            # ภาพEN: Veo รับอังกฤษเท่านั้น — ใช้ visual EN ที่แนบใน queue (Day-1: เติมให้ครบ)
            prompt_en = seg.get("prompt_en") or seg["title"]
            res = generate_segment(prompt_en)
            self._ledger(seg, res)
            if res["ok"]:
                fired.append(f"{seg['id']}→{res['request_id']}")
                self._mark(seg, res["request_id"])
            else:
                self._alert(f"media_daily เจนเสีย {seg['id']}: {res['error']}")
                fired.append(f"{seg['id']}❌")
        return f"✅ media_daily ยิง {len(fired)}/{MAX_PER_DAY}: " + ", ".join(fired)

    def _due_segments(self) -> list[dict]:
        segs = []
        for line in QUEUE.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\|\s*(\d+)\s*\|([^|]*)\|\s*✅ approved[^\|]*\|\s*—\s*\|", line)
            if m:
                segs.append({"id": m.group(1), "title": m.group(2).strip(),
                             "prompt_en": ""})
        return segs

    def _ledger(self, seg: dict, res: dict) -> None:
        okm = "ผ่าน" if res["ok"] else "เสีย"
        err = "" if res["ok"] else res.get("error", "")[:60]
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(f"| {date.today()} | {seg['id']} | omni-720p | {okm} "
                    f"| ~15 | — | {res.get('request_id', err)} |\n")

    def _mark(self, seg: dict, rid: str) -> None:
        text = QUEUE.read_text(encoding="utf-8")
        text = text.replace(f"| {seg['id']} |", f"| {seg['id']} |", 1)
        # เติม request_id ลงแถว (คอลัมน์ request_id ยังเป็น —)
        lines = []
        for line in text.splitlines():
            if re.match(rf"\|\s*{seg['id']}\s*\|", line) and "| — |" in line:
                line = line.replace("| — |", f"| {rid} |", 1)
            lines.append(line)
        QUEUE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _alert(self, msg: str) -> None:
        try:
            subprocess.run(
                [sys.executable, "scripts/inbox.py", "send", "ceo", "__human__",
                 "[media_daily] แจ้ง Owner", msg],
                capture_output=True, timeout=30,
                cwd=str(Path(__file__).parent.parent.parent),
            )
        except Exception:
            pass

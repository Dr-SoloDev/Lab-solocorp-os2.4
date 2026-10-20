"""News Daily — ดึงข่าวรายแผนก → facts store → inbox

ทำงานทุกเช้า (date-gate หลัง 06:00) ตาม watchlist ที่ Owner ดูแลเอง
ที่ `bus/news/watchlist.md`

ลำดับ:
  1. อ่าน watchlist (เฉพาะแถว ✅ active)
  2. ดึงข่าว (rss = เร็ว 0 RAM | web = Chromium 47.5MB)
  3. ตัดข่าวซ้ำ (bus/news/seen.json)
  4. แยกตามแผนก → เขียน facts key="news.<dept>.<วันที่>"
  5. ส่ง inbox ให้แผนก

agent ดึงข่าวได้ผ่าน Bus:
  POST /v1/context {"agent_id": "cmo-mark", "keys": ["news.cmo.*"]}
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..runner import Loop
from ..state import last_run

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from solocorp_skills.news import (  # noqa: E402
    build_digest,
    dedupe,
    fetch_source,
    group_by_dept,
    load_seen,
    load_watchlist,
    save_seen,
)

BUS_URL = os.environ.get("SOLOCORP_BUS_URL", "http://127.0.0.1:8099")
API_KEY = os.environ.get("SOLOCORP_API_KEY", "sk-solocorp-admin-local-dev-001")

MAX_SOURCES_PER_RUN = 15
MAX_ITEMS_PER_SOURCE = 15
MAX_ITEMS_PER_DEPT = 25

# แผนก → inbox profile (ชื่อที่ scripts/inbox.py รู้จัก — ไม่ใช่ agent_id)
DEPT_INBOX = {
    "ceo": "ceo",
    "cmo": "cmo",
    "sales": "sales",
    "support": "support",
    "content": "content-creator",
    "product": "product",
    "engineering": "engineering",
    "cfo": "cfo",
    "legal": "legal",
}

# ผู้ส่ง (inbox รับได้เฉพาะ profile ที่มีอยู่ — news_daily ไม่ใช่ profile)
INBOX_FROM = "ceo"


def _post_fact(key: str, value: dict) -> bool:
    """เขียน fact เข้าคลังความรู้ผ่าน Bus"""
    body = json.dumps({
        "key": key,
        "value": value,
        "metadata": {"workstream": "OWN-BIZ", "sensitivity": "PUB"},
        "updated_by": "news_daily",
    }, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f"{BUS_URL}/v1/facts",
        data=body,
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=15).read()
        return True
    except Exception as e:
        print(f"⚠️ เขียน fact '{key}' ไม่สำเร็จ: {e}", file=sys.stderr)
        return False


def _notify(dept: str, subject: str, body: str) -> bool:
    """ส่งข้อความเข้า inbox ของแผนก"""
    target = DEPT_INBOX.get(dept)
    if not target:
        print(f"⚠️ ไม่รู้จัก inbox ของแผนก '{dept}' — ข้าม", file=sys.stderr)
        return False
    try:
        r = subprocess.run(
            [sys.executable, "scripts/inbox.py", "send", INBOX_FROM, target,
             subject, body[:1500]],
            capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        if r.returncode != 0 or "ไม่รู้จัก" in (r.stdout or ""):
            print(f"⚠️ ส่ง inbox ให้ {dept} ไม่สำเร็จ: "
                  f"{(r.stdout or r.stderr or '').strip()[:120]}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"⚠️ ส่ง inbox ให้ {dept} ไม่สำเร็จ: {e}", file=sys.stderr)
        return False


class NewsDailyLoop(Loop):
    loop_id = "news_daily"
    interval = timedelta(hours=20)  # fallback; หลักคือ date-gate ข้างล่าง
    trust_level = 1  # L1 report only — เขียน facts + ส่ง inbox เท่านั้น
    model_hint = None  # ไม่ใช้ LLM — ดึง RSS ตรง ไม่เผาเครดิต

    def should_run(self) -> bool:
        last = last_run(self.loop_id)
        if last is not None and last.date() >= date.today():
            return False  # วันนี้ดึงแล้ว
        return datetime.now().hour >= 6  # เช้าเท่านั้น

    def run(self) -> str:
        sources = load_watchlist()
        if not sources:
            return "⏭ news_daily: ไม่มีแหล่งข่าวใน watchlist (bus/news/watchlist.md)"

        sources = sources[:MAX_SOURCES_PER_RUN]
        all_items = []
        errors: list[str] = []

        for src in sources:
            try:
                items = fetch_source(src)
                all_items.extend(items)
            except Exception as e:
                errors.append(f"{src.name}: {type(e).__name__}")

        if not all_items:
            msg = f"⏭ news_daily: ไม่ได้ข่าวเลย ({len(sources)} แหล่ง"
            if errors:
                msg += f" · ผิดพลาด {len(errors)}: {', '.join(errors[:3])}"
            return msg + ")"

        seen = load_seen()
        fresh, seen = dedupe(all_items, seen)

        if not fresh:
            save_seen(seen)
            return (f"⏭ news_daily: ไม่มีข่าวใหม่ "
                    f"(ดึง {len(all_items)} ข่าว · เดิมทั้งหมด)")

        by_dept = group_by_dept(fresh)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        written = 0
        notified = 0

        for dept, items in by_dept.items():
            items = items[:MAX_ITEMS_PER_DEPT]
            digest = build_digest(items, dept)
            payload = {
                "date": today,
                "dept": dept,
                "count": len(items),
                "digest": digest,
                "items": [
                    {"title": it.title, "url": it.url, "source": it.source}
                    for it in items
                ],
            }
            if _post_fact(f"news.{dept}.{today}", payload):
                written += 1
                _notify(dept, f"📰 ข่าวสาขา {dept} — {today} ({len(items)} ข่าว)",
                        digest)
                notified += 1

        save_seen(seen)

        msg = (f"✅ news_daily: ส่งข่าว {len(fresh)} ข่าว → {written} แผนก "
               f"({notified} inbox) · ดึงจาก {len(sources)} แหล่ง")
        if errors:
            msg += f" · ข้าม {len(errors)} แหล่งที่ผิดพลาด"
        return msg

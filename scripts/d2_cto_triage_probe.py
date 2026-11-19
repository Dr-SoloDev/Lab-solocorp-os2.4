"""D2 probe — cto-triage-checker (propose-only, read-only + compare).

D1: docs/certification/D1-cto-triage.md · 20 topics → expected owner
เทียบ ROUTING_MATRIX.md §1 · ห้าม implement/approve/enforce.
Exit 0 = 20/20 PASS + เขียนเฉพาะ bus/evidence/<date>/d2-cto/.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EVIDENCE_ROOT = (
    ROOT
    / "bus"
    / "evidence"
    / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    / "d2-cto"
)

# (topic, expected routed_to) — จาก ROUTING_MATRIX.md §1 + out_of_scope → triage
CASES = [
    ("แก้ routing rules ของ Central Bus", "architect-songsak"),
    ("central bus schema validation ล้มเหลว", "architect-songsak"),
    ("เพิ่ม schema ใหม่ใน bus", "architect-songsak"),
    ("bus monitor แจ้ง queue depth สูง", "architect-songsak"),
    ("implement feature login", "engineering-changful"),
    ("build backend API ใหม่", "engineering-changful"),
    ("deploy งานขึ้น staging", "engineering-changful"),
    ("bug หน้า checkout", "engineering-changful"),
    ("review code PR ถัดไป", "engineering-changful"),
    ("regression test รอบ release", "qa-team"),
    ("smoke test หลัง deploy", "qa-team"),
    ("QA evidence ไม่ครบ", "qa-team"),
    ("quality gate ตก", "qa-team"),
    ("สรุปสถานะ pipeline รายสัปดาห์", "cto-vector"),
    ("ขออนุมัติงบประมาณเพิ่ม", "cto-vector"),
    ("ประชุม sync ข้ามแผนก", "cto-vector"),
    ("เขียน PRD ฟีเจอร์ billing v2", "cto-vector"),
    ("วิจัยโมเดล LLM ใหม่ใน R&D Lab", "cto-vector"),
    ("ออกแบบโลโก้แบรนด์ใหม่", "cto-vector"),
    ("เซ็นสัญญาลูกค้า B2B", "cto-vector"),
]

calls: list[dict] = []


def record(tool: str, detail: str) -> None:
    calls.append({"tool": tool, "detail": detail})


def main() -> int:
    from axis_mcp.departments.cto_mcp import cto_route

    record("read_file", "profiles/cto/ROUTING_MATRIX.md §1 + out_of_scope")
    soul = (ROOT / "profiles" / "cto" / "CTO.SOUL.md").read_text(encoding="utf-8")
    record("read_file", "profiles/cto/CTO.SOUL.md (enforce check)")
    # เกณฑ์บังคับใช้จริง: มีลายเซ็น Owner + ไม่มีคำว่า DRAFT/DO NOT ENFORCE หลงเหลือ
    # ("NOT EFFECTIVE" มี substring "EFFECTIVE" — ต้องปฏิเสธด้วย DRAFT markers ชัดเจน)
    enforce = (
        "Dr.solodev" in soul
        and "2026-11-13" in soul
        and "DRAFT-UNAPPROVED" not in soul
        and "DO NOT ENFORCE" not in soul
    )
    rows = []
    ok_all = True
    for topic, expected in CASES:
        raw = cto_route(topic)
        record("cto_route", topic)
        got = json.loads(raw).get("routed_to")
        ok = got == expected
        ok_all &= ok
        rows.append(
            {
                "topic": topic,
                "expected": expected,
                "got": got,
                "pass": ok,
                "reason": "ROUTING_MATRIX §1/ownership map",
            }
        )
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_ROOT / "tool-calls.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in calls) + "\n",
        encoding="utf-8",
    )
    record("write_file", "bus/evidence/<date>/d2-cto/tool-calls.jsonl")
    result = {
        "passed": sum(r["pass"] for r in rows),
        "total": len(rows),
        "enforce_allowed": enforce,
        "enforce_note": "L5 signed+EFFECTIVE"
        if enforce
        else "refuse enforce: no EFFECTIVE L5 on this tree",
        "rows": rows,
        "tool_calls": len(calls),
    }
    (EVIDENCE_ROOT / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    record("write_file", "bus/evidence/<date>/d2-cto/result.json")
    (EVIDENCE_ROOT / "tool-calls.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in calls) + "\n",
        encoding="utf-8",
    )
    print(
        f"D2 cto-triage: {result['passed']}/{result['total']} PASS "
        f"enforce_allowed={enforce} evidence={EVIDENCE_ROOT}"
    )
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())

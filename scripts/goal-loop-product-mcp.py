#!/usr/bin/env python3
"""Goal Loop — T3 Product MCP D1 (loop จนกว่าจะผ่าน 5 ข้อ)

วิ่งจนกว่า D1 ครบ 5 เส้นชัย (README §5). ใช้ได้ซ้ำทุกครั้ง.
- loop 1: parse structure
- loop 2: content completeness
- loop 3: recommendation present
จบ loop ไม่ผ่าน → exit 1; ผ่าน → exit 0 + เขียน evidence
"""

import json, sys, pathlib, datetime

DOC = pathlib.Path(
    "/data/projects/Lab-solocorp-os2.4/docs/certification/D1-product-mcp.md"
)
OUT = pathlib.Path(
    "/data/projects/Lab-solocorp-os2.4/bus/evidence/2026-11-09/product-mcp-d1"
)
OUT.mkdir(parents=True, exist_ok=True)

checks = []


def chk(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"[{'✅' if ok else '❌'}] {name}: {detail}")


text = DOC.read_text() if DOC.exists() else ""
chk("file exists", DOC.exists(), str(DOC))
chk("0 status", "## 0." in text and "overclaim" in text, "มี §0 status จริง")
chk("1 what", "## 1." in text and "PRD + Roadmap" in text, "ระบุขอบเขต PRD+Roadmap")
chk(
    "2 why agent", "## 2." in text and "ตัดสินใจ trade-off" in text, "เหตุผล why agent ครบ"
)
chk(
    "3 tools",
    "## 3." in text
    and all(
        x in text
        for x in [
            "product_department_info",
            "product_list_features",
            "product_create_prd",
            "product_prioritize",
        ]
    ),
    "4 tools ครบ",
)
chk(
    "4 permission",
    "## 4." in text and "ห้ามเขียนนอก" in text and "D0" in text,
    "permission scope + guard อ่อน",
)
chk(
    "5 finish line",
    "## 5." in text and "Maker ≠ Checker" in text,
    "เส้นชัย 5 ข้อ + checker",
)
chk(
    "6 options",
    "## 6." in text and all(x in text for x in ["A. Standalone", "B. รวมเข้า", "C. รอ"]),
    "3 ทางเลือกครบ",
)
chk(
    "7 recommend A",
    "## 7." in text and "เลือก A" in text and "FR-07" in text,
    "แนะนำ A + FR-07",
)

passed = all(c["ok"] for c in checks)
report = {
    "goal": "T3 Product MCP D1",
    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "path": str(DOC),
    "passed": passed,
    "checks": checks,
    "seats": f"{sum(c['ok'] for c in checks)}/{len(checks)}",
    "for_owner_at": "2026-11-09 18:00",
}
(OUT / "goal-loop-report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2)
)
print(f"\nGOAL LOOP RESULT: {'PASS' if passed else 'FAIL'}  {report['seats']}")
print(f"evidence: {OUT / 'goal-loop-report.json'}")
sys.exit(0 if passed else 1)

#!/usr/bin/env python3
"""
certification-audit.py — ตรวจสถานะบันได 4 ด่าน (D0–D4) ของทุกแผนกจากของจริงใน repo

ไม่เชื่อทะเบียน — ตรวจจากหลักฐานในไฟล์จริง แล้วเทียบกับ profiles/CERTIFICATION-REGISTRY.md

ใช้:
  python scripts/certification-audit.py                # รายงานบนจอ
  python scripts/certification-audit.py --json out.json # เขียนหลักฐาน JSON
  python scripts/certification-audit.py --strict       # exit 1 ถ้าทะเบียนไม่ตรงกับของจริง

เกณฑ์ (rules/06-certification.md §2):
  D1 = มีเอกสาร 1 หน้าตาม sop/TEMPLATE-D1-agent-rationale.md (ครบ 5 ข้อ)
  D2 = มี mini-agent 50–150 บรรทัด ที่เรียกเครื่องมือจริง + มีหลักฐานการรัน (output + exit code)
  D3 = มีตารางประเมิน ≥20 แถว ตาม sop/TEMPLATE-D3-evaluation-table.md
  D4 = มี runbook + ผลรันของคน/agent คนละตัว
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "profiles"
WORKERS = ROOT / "workers"
EVIDENCE = ROOT / "bus" / "evidence"
REGISTRY = PROFILES / "CERTIFICATION-REGISTRY.md"

# แผนก → ไฟล์ worker implementation
DEPT_WORKER = {
    "01-ceo": None,  # CEO ไม่มี worker (เป็นตัวเราเอง)
    "02-cfo": "cfo_agent.py",
    "02-coo": "coo_dispatch_agent.py",
    "03-cmo": "cmo_agent.py",
    "04-orchestrator": "orchestrator_agent.py",
    "05-architect": "architect_agent.py",
    "06-product": "product_agent.py",
    "07-engineering": "engineering_agent.py",
    "08-design": "design_agent.py",
    "09-ui-designer": "ui_agent.py",
    "10-qa": "qa_agent.py",
    "11-sales": "sales_agent.py",
    "12-support": "support_agent.py",
    "13-legal": "legal_agent.py",
    "14-web3": "web3_agent.py",
    "15-content-creator": "content_agent.py",
    "16-neteng": "neteng_agent.py",
    "17-cybersec": "cybersec_agent.py",
    "18-psychology": "psychology_agent.py",
    "19-rd-lab": "rd_lab_agent.py",
}

TOOL_PATTERNS = (
    r"\bllm_provider\b", r"LLMProvider", r"\.think\(", r"subprocess\.",
    r"\bhttpx\b", r"\brequests\.", r"\.read_text\(", r"\.write_text\(",
    r"\.read_bytes\(", r"\.write_bytes\(", r"os\.walk", r"glob\(", r"Path\(",
    r"json\.dump", r"json\.load", r"publish", r"enqueue",
)


def _lines(p: Path) -> int:
    try:
        return len(p.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0


def _has_tool_calls(p: Path) -> int:
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return sum(1 for pat in TOOL_PATTERNS if re.search(pat, src))


def find_d1(dept_id: str) -> list[str]:
    """เอกสาร D1 ของแผนก — ค้นใน profiles/ และ bus/evidence/"""
    hits: list[str] = []
    for root in (PROFILES, EVIDENCE):
        if not root.exists():
            continue
        for f in root.rglob("*.md"):
            name = f.name.lower()
            rel = str(f.relative_to(ROOT)).lower()
            if "d1" in name and (dept_id in rel or dept_id.split("-", 1)[-1] in rel):
                hits.append(str(f.relative_to(ROOT)))
    return hits


def find_d2_evidence(dept_id: str) -> list[str]:
    """หลักฐาน D2 ของแผนก — ไฟล์ใน bus/evidence/ ที่พูดถึงแผนก/agent ตัวนั้น"""
    hits: list[str] = []
    if not EVIDENCE.exists():
        return hits
    token = dept_id.split("-", 1)[-1].replace("-", "")
    for f in EVIDENCE.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in {".md", ".json", ".txt", ".log"}:
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")[:20000]
        except OSError:
            continue
        if dept_id in txt or token in txt.lower():
            hits.append(str(f.relative_to(ROOT)))
    return hits


def find_d3(dept_id: str) -> list[str]:
    hits: list[str] = []
    for root in (EVIDENCE, PROFILES, ROOT / "docs"):
        if not root.exists():
            continue
        for f in root.rglob("*.md"):
            n = f.name.lower()
            if "d3" in n or "eval" in n:
                rel = str(f.relative_to(ROOT)).lower()
                if dept_id in rel or dept_id.split("-", 1)[-1] in rel:
                    hits.append(str(f.relative_to(ROOT)))
    return hits


def registry_claims() -> dict[str, dict[str, bool]]:
    """อ่านสถานะที่ประกาศไว้ในทะเบียน → {dept_id: {D1:bool,...}}

    รองรับ 2 รูปแบบของคอลัมน์ชื่อ:
      | `15-content-creator` (content) | ... |   ← dept id ใน backtick
      | **content-creator-sek** (content) | ... |   ← ชื่อ agent
    """
    if not REGISTRY.exists():
        return {}

    # สร้างดัชนี: agent name → dept id (เช่น content-creator-sek → 15-content-creator)
    agent_index: dict[str, str] = {}
    for dept_id in DEPT_WORKER:
        slug = dept_id.split("-", 1)[-1]
        agent_index[slug] = dept_id
        agent_index[slug.replace("-", "_")] = dept_id
    agent_index["content-creator-sek"] = "15-content-creator"

    out: dict[str, dict[str, bool]] = {}
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "D1" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 6:
            continue
        first = cells[0].replace("*", "").strip()
        dept_id: str | None = None

        m = re.search(r"`(\d\d-[a-z0-9\-]+)`", first)
        if m:
            dept_id = m.group(1)
        else:
            # ชื่อ agent ในวงเล็บ เช่น (content-creator-sek) หรือ (15-content-creator)
            for token in re.findall(r"\(([a-z0-9\-_]+)\)", first):
                if token in agent_index:
                    dept_id = agent_index[token]
                    break
                if re.fullmatch(r"\d\d-[a-z0-9\-]+", token):
                    dept_id = token
                    break
            if dept_id is None:
                slug = re.split(r"[\s(]", first)[0].strip("`-")
                if slug in agent_index:
                    dept_id = agent_index[slug]

        if not dept_id:
            continue
        flags = {}
        for i, key in enumerate(("D1", "D2", "D3", "D4"), start=1):
            flags[key] = "✅" in cells[i]
        out[dept_id] = flags
    return out


def audit() -> dict:
    claims = registry_claims()
    rows = []
    for dept_id in sorted(DEPT_WORKER):
        d = PROFILES / dept_id
        worker_name = DEPT_WORKER[dept_id]
        worker = WORKERS / "agents" / worker_name if worker_name else None
        soul = d / "SOUL.md"

        specialists = list(d.rglob("*.SOUL.md")) if d.exists() else []
        specialists = [s for s in specialists if s.name != "SOUL.md"]

        w_lines = _lines(worker) if worker and worker.exists() else 0
        w_tools = _has_tool_calls(worker) if worker and worker.exists() else 0

        d1 = find_d1(dept_id)
        d2_ev = find_d2_evidence(dept_id)
        d3 = find_d3(dept_id)

        # D2 ต้องครบ 3 อย่าง: มี worker, 50-150 บรรทัด, เรียกเครื่องมือจริง + มีหลักฐานรัน
        d2_code = bool(worker and worker.exists() and 50 <= w_lines <= 150 and w_tools > 0)
        d2 = d2_code and bool(d2_ev)

        rows.append({
            "dept": dept_id,
            "soul": soul.exists(),
            "specialists": len(specialists),
            "worker": worker_name or "-",
            "worker_lines": w_lines,
            "worker_tool_patterns": w_tools,
            "d1_docs": d1,
            "d2_code_ok": d2_code,
            "d2_evidence": d2_ev[:3],
            "d3_docs": d3,
            "registry": claims.get(dept_id),
        })

    # ตรวจความสอดคล้อง: ทะเบียนอ้างว่าผ่าน แต่ของจริงไม่มี
    mismatches = []
    for r in rows:
        reg = r["registry"]
        if not reg:
            continue
        actual = {
            "D1": bool(r["d1_docs"]),
            "D2": bool(r["d2_code_ok"] and r["d2_evidence"]),
            "D3": bool(r["d3_docs"]),
        }
        for gate in ("D1", "D2", "D3"):
            if reg.get(gate) and not actual[gate]:
                mismatches.append({
                    "dept": r["dept"], "gate": gate,
                    "reason": "ทะเบียนอ้างว่าผ่าน แต่ไม่มีหลักฐานใน repo",
                })

    return {
        "generated_by": "scripts/certification-audit.py",
        "depts_audited": len(rows),
        "rows": rows,
        "registry_mismatches": mismatches,
        "totals": {
            "d1": sum(1 for r in rows if r["d1_docs"]),
            "d2_code_ok": sum(1 for r in rows if r["d2_code_ok"]),
            "d2_full": sum(1 for r in rows if r["d2_code_ok"] and r["d2_evidence"]),
            "d3": sum(1 for r in rows if r["d3_docs"]),
            "specialists_total": sum(r["specialists"] for r in rows),
            "workers_50_150": sum(
                1 for r in rows if 50 <= r["worker_lines"] <= 150 and r["worker_tool_patterns"] > 0
            ),
        },
    }


def report(result: dict) -> None:
    t = result["totals"]
    print()
    print("=" * 96)
    print("CERTIFICATION LADDER AUDIT — ตรวจจากหลักฐานใน repo (ไม่เชื่อทะเบียน)")
    print("=" * 96)
    hdr = f"{'DEPT':<20}{'SPEC':>5}{'WORKER':<24}{'LINES':>6}{'TOOLS':>6}{'D1':>4}{'D2':>4}{'D3':>4}  NOTE"
    print(hdr)
    print("-" * 96)
    for r in result["rows"]:
        d1 = "✓" if r["d1_docs"] else "·"
        d2 = "✓" if (r["d2_code_ok"] and r["d2_evidence"]) else ("code" if r["d2_code_ok"] else "·")
        d3 = "✓" if r["d3_docs"] else "·"
        note = []
        if r["worker_lines"] and not (50 <= r["worker_lines"] <= 150):
            note.append(f"worker {r['worker_lines']}L ไม่อยู่ในช่วง 50-150")
        if r["worker_tool_patterns"] == 0 and r["worker"] != "-":
            note.append("ไม่พบการเรียกเครื่องมือ")
        if r["registry"] and r["registry"].get("D2") and not (r["d2_code_ok"] and r["d2_evidence"]):
            note.append("⚠ ทะเบียนอ้าง D2 แต่ของจริงไม่มี")
        if r["registry"] and r["registry"].get("D1") and not r["d1_docs"]:
            note.append("⚠ ทะเบียนอ้าง D1 แต่ไม่มีเอกสาร")
        print(f"{r['dept']:<20}{r['specialists']:>5}{(r['worker'] or '-'):<24}"
              f"{r['worker_lines']:>6}{r['worker_tool_patterns']:>6}{d1:>4}{d2:>4}{d3:>4}  {'; '.join(note)}")

    print("-" * 96)
    print(f"สรุป: D1 มีเอกสาร {t['d1']}/{result['depts_audited']} · "
          f"D2 โค้ดผ่านเกณฑ์ {t['d2_code_ok']}/{result['depts_audited']} · "
          f"D2 ครบ (โค้ด+หลักฐาน) {t['d2_full']}/{result['depts_audited']} · "
          f"D3 {t['d3']}/{result['depts_audited']}")
    print(f"specialists รวม {t['specialists_total']} · worker ที่อยู่ในช่วง 50-150 บรรทัด {t['workers_50_150']}")

    if result["registry_mismatches"]:
        print()
        print("🚨 ทะเบียนไม่ตรงกับของจริง:")
        for m in result["registry_mismatches"]:
            print(f"   · {m['dept']} {m['gate']} — {m['reason']}")
    else:
        print("\n✅ ทะเบียนตรงกับหลักฐานใน repo (ไม่มีการอ้างเกินจริง)")
    print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="เขียนผลลัพธ์เป็น JSON (หลักฐาน)")
    ap.add_argument("--strict", action="store_true", help="exit 1 ถ้าทะเบียนไม่ตรง")
    args = ap.parse_args()

    result = audit()
    report(result)

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"📄 หลักฐาน: {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")

    if args.strict and result["registry_mismatches"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

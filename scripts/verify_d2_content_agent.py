#!/usr/bin/env python3
"""D2 independent verifier — content-creator-sek

ผู้ตรวจ ≠ ผู้ทำ: script นี้ **ไม่เชื่อผลที่ agent รายงานเอง**
มันอ่านไฟล์ที่เกิดขึ้นจริงจากดิสก์ แล้วตรวจ 6 เกณฑ์ตาม D1 §5

Usage:
    python scripts/verify_d2_content_agent.py --brief <path> [--out <path>] [--json <path>]

Exit codes: 0 = ผ่านครบ 6 ข้อ · 1 = ไม่ผ่าน · 2 = รัน agent ไม่ได้
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

BRAND_SOURCES = (
    "profiles/01-ceo/SOUL.md",
    "profiles/03-cmo/SOUL.md",
    "docs/brand/BRAND-GUIDELINES-v1.md",
)
SECTIONS = ("## Hook", "## Body", "## CTA", "## Hashtags")
MIN_CHARS, MAX_CHARS = 600, 2500
DRAFTS = REPO / "bus" / "creative" / "drafts"


# สแกนเฉพาะ root ที่มีความหมาย (กันเดินทั้ง repo + vendored venv)
SCAN_ROOTS = ("bus", "scripts", "workers", "profiles", "docs", "decisions", "rules", "sop")
SKIP_PARTS = {".git", ".jj", ".venv", "venv", "__pycache__", "node_modules", ".codegraph"}


def _snapshot() -> set[str]:
    """ไฟล์ใน root ที่มีความหมาย — ใช้แทน git status ที่ ignore ปิดบัง"""
    out = set()
    for root in SCAN_ROOTS:
        base = REPO / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and not any(part in SKIP_PARTS for part in p.parts):
                out.add(str(p))
    return out


def _read_log(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    rows = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({"tool": "CORRUPT", "raw": line})
    return rows


async def _run_agent(brief: Path, out: Path | None, log: Path) -> dict:
    from workers.agents.content_agent import ContentAgent

    agent = ContentAgent(log_path=str(log))
    params = {"brief_path": str(brief)}
    if out:
        params["out_path"] = str(out)
    return await agent.execute(
        {"payload": {"description": "", "params": params}}
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--log", default="bus/evidence/2026-10-23/d2-content-creator/tool-calls-verify.jsonl")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    brief = Path(args.brief)
    log = REPO / args.log
    log.unlink(missing_ok=True)

    before = _snapshot()
    try:
        result = asyncio.run(_run_agent(brief, Path(args.out) if args.out else None, log))
    except Exception as exc:  # noqa: BLE001
        print(f"❌ รัน agent ไม่ได้: {exc}")
        return 2

    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    calls = _read_log(log)
    read_paths = [c.get("args") for c in calls if c.get("tool") == "read_file"]

    # 1) อ่าน SOUL ×2 + brand guidelines
    missing_src = [s for s in BRAND_SOURCES if s not in read_paths]
    check("1 อ่าน brand sources ครบ 3", not missing_src,
          f"อ่านแล้ว {len(read_paths)} ไฟล์" + (f" · ขาด {missing_src}" if missing_src else ""))

    # 2) อ่าน brief
    check("2 อ่าน brief", any(str(brief) in str(p) or "brief" in str(p) for p in read_paths),
          f"brief={brief}")

    # 3) เขียน draft จริง
    # ⚠️ agent ที่ล้มเหลวจะไม่มี details.out_path → Path("") == Path(".")
    #    ซึ่ง exists() = True (repo root) แล้ว read_text() โยน IsADirectoryError
    #    → ต้องเช็ค "เป็นไฟล์จริง" ก่อนแตะเนื้อหา แล้วรายงานเป็น verdict ไม่ใช่ traceback
    raw_out = str((result.get("details") or {}).get("out_path", "") or "")
    out_path = Path(raw_out) if raw_out else None
    text = ""
    out_err = ""
    if out_path is None:
        out_err = "ไม่มี out_path ในผลของ agent"
    elif not out_path.is_file():
        out_err = f"ไม่ใช่ไฟล์ (exists={out_path.exists()})"
    else:
        try:
            text = out_path.read_text(encoding="utf-8")
        except OSError as exc:
            out_err = f"อ่านไม่ได้: {exc}"
    check("3 เขียนไฟล์ draft", not out_err,
          str(out_path) if not out_err else f"{raw_out or '(ไม่มี out_path)'} — {out_err}")

    # 4) ครบ 4 องค์ประกอบ
    missing_sec = [s for s in SECTIONS if s not in text]
    detail4 = f"missing={missing_sec or 'none'}"
    if out_err:
        detail4 = f"ตรวจไม่ได้ — {out_err}"
    check("4 ครบ 4 องค์ประกอบ", not missing_sec, detail4)

    # 5) ความยาว (นับเอง ไม่เชื่อ agent)
    chars = len(text)
    detail5 = f"{chars} chars"
    if out_err:
        detail5 = f"ตรวจไม่ได้ — {out_err}"
    check(f"5 ความยาว {MIN_CHARS}-{MAX_CHARS}", MIN_CHARS <= chars <= MAX_CHARS, detail5)

    # 6) ไม่เขียนนอกขอบเขต
    after = _snapshot()
    new_files = [f for f in (after - before) if Path(f).is_relative_to(DRAFTS)
                 or Path(f).is_relative_to(log.parent)]
    leaked = sorted(after - before - set(new_files))
    check("6 ไม่เขียนนอกขอบเขต", not leaked, f"leaked={leaked or 'none'}")

    passed = all(c["ok"] for c in checks)
    payload = {
        "agent_result": result,
        "checks": checks,
        "passed": passed,
        "tool_call_count": len(calls),
        "brief": str(brief),
    }
    if args.json:
        Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'=' * 68}")
    for c in checks:
        print(f"{'✅' if c['ok'] else '❌'} {c['check']:<34} {c['detail']}")
    print(f"{'=' * 68}")
    print(f"agent status = {result.get('status')} · tool calls = {len(calls)}")
    print(f"D2 VERDICT: {'PASSED' if passed else 'RETURNED'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""ตรวจสุขภาพ LLM model chain — ใช้ก่อนเพิ่ม/เปลี่ยนโมเดลใน workers/llm_provider.py

โมเดลฟรีของ opencode ถูกเปลี่ยนชื่อ/ลบไปเรื่อย ๆ → ถ้าชื่อใน chain ไม่มีจริง
ทุกโมเดลจะคืน "empty response" → agent 19 ตัว "ตาบอด" **โดยไม่มี error ชัดเจน**

ใช้:
  python scripts/check-model-health.py                       # ตรวจชื่อ (เร็ว ~4s)
  python scripts/check-model-health.py --verify <model>      # ทดสอบจริง 1 โมเดล
  python scripts/check-model-health.py --verify-all          # ทดสอบจริงทุกตัวใน chain
  python scripts/check-model-health.py --candidates          # ลองโมเดลใหม่ที่ยังไม่อยู่ใน chain
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OPENCODE = Path.home() / ".opencode" / "bin" / "opencode"
PROBE = "ตอบว่า OK เท่านั้น"
TIMEOUT = 90

# error ที่บอกว่าโมเดลนี้ใช้ไม่ได้ (ไม่ใช่แค่ช้า)
DEAD_MARKERS = (
    "model not found",
    "agents_md",
    "unknown_parameter",
    "unsupported_parameter",
)


def probe_model(model: str) -> dict:
    """ทดสอบโมเดลจริง — จำลองวิธีที่ llm_provider เรียก (cwd = repo root!)

    cwd สำคัญมาก: ตอนรันจากโปรเจกต์ opencode จะส่ง CLAUDE.md/AGENTS.md
    เป็น parameter ชื่อ agents_md → free-tier gateway ปฏิเสธ
    """
    if not OPENCODE.exists():
        return {"model": model, "ok": False, "reason": "ไม่พบ opencode binary"}

    try:
        r = subprocess.run(
            [str(OPENCODE), "run", "--pure", "--model", model],
            input=PROBE, capture_output=True, text=True,
            timeout=TIMEOUT, cwd=str(ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"model": model, "ok": False, "reason": f"timeout ({TIMEOUT}s)"}
    except Exception as e:
        return {"model": model, "ok": False, "reason": f"{type(e).__name__}: {e}"}

    out = (r.stdout or "") + (r.stderr or "")
    low = out.lower()
    for marker in DEAD_MARKERS:
        if marker in low:
            return {"model": model, "ok": False, "reason": f"gateway ปฏิเสธ ({marker})",
                    "detail": out.strip()[:200]}

    # ต้องมีข้อความตอบจริง (ไม่ใช่แค่ banner)
    text = out.strip()
    if not text or "Error" in text:
        return {"model": model, "ok": False, "reason": "ไม่ได้ข้อความตอบ",
                "detail": text[:200]}

    return {"model": model, "ok": True, "reason": "ใช้ได้", "detail": text[-120:]}


def main() -> int:
    ap = argparse.ArgumentParser(description="ตรวจสุขภาพ LLM model chain")
    ap.add_argument("--verify", metavar="MODEL", help="ทดสอบโมเดล 1 ตัวจริง")
    ap.add_argument("--verify-all", action="store_true", help="ทดสอบทุกตัวใน chain")
    ap.add_argument("--candidates", action="store_true",
                    help="ทดสอบโมเดลใหม่ที่ยังไม่อยู่ใน chain")
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    args = ap.parse_args()

    from workers.llm_provider import audit_models, MODEL_FALLBACKS, DEAD_MODELS

    # ── โหมดทดสอบจริง ──
    if args.verify:
        r = probe_model(args.verify)
        print(f"{'✅' if r['ok'] else '❌'} {r['model']} — {r['reason']}")
        if r.get("detail"):
            print(f"   {r['detail']}")
        return 0 if r["ok"] else 1

    if args.verify_all:
        print("=== ทดสอบจริงทุกโมเดลใน chain ===")
        ok = 0
        for m in MODEL_FALLBACKS:
            r = probe_model(m)
            ok += 1 if r["ok"] else 0
            print(f"{'✅' if r['ok'] else '❌'} {m:44} {r['reason']}")
        print(f"--- {ok}/{len(MODEL_FALLBACKS)} ใช้ได้ ---")
        return 0 if ok == len(MODEL_FALLBACKS) else 1

    if args.candidates:
        report = audit_models(use_cache=True)
        cands = [m for m in report.get("candidates", []) if m not in DEAD_MODELS]
        print(f"=== ทดสอบโมเดลใหม่ {len(cands)} ตัว ===")
        usable = []
        for m in cands:
            r = probe_model(m)
            print(f"{'✅' if r['ok'] else '❌'} {m:44} {r['reason']}")
            if r["ok"]:
                usable.append(m)
        if usable:
            print("\nเพิ่มเข้า MODEL_FALLBACKS ได้:")
            for m in usable:
                print(f'    "{m}",')
        return 0

    # ── โหมดตรวจชื่อ (เร็ว) ──
    report = audit_models(use_cache=False)
    print("=== LLM Model Chain Health ===")
    print(f"ตรวจเมื่อ: {report.get('checked_at')}")
    print(f"chain ({len(report.get('chain', []))}):")
    for m in report.get("chain", []):
        mark = "✅" if m in report.get("usable", []) else "❌ ไม่มีจริง"
        print(f"   {mark}  {m}")
    if report.get("missing"):
        print(f"\n🚨 หายไป {len(report['missing'])} ตัว: {report['missing']}")
        print("   แก้ workers/llm_provider.py MODEL_FALLBACKS")
    else:
        print("\n✅ chain สมบูรณ์ — ไม่มีโมเดลหาย")
    if report.get("candidates"):
        print(f"\nโมเดลใหม่ที่ยังไม่อยู่ใน chain ({len(report['candidates'])}):")
        for m in report["candidates"][:8]:
            print(f"   · {m}")
        print("   ทดสอบ: python scripts/check-model-health.py --candidates")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())

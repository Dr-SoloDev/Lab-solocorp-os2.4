#!/usr/bin/env python3
"""Quality probe — วัดคุณภาพโมเดลด้วยงานจริง (content draft ไทย 4 หัวข้อ)

ใช้ prompt เดียวกับ workers/agents/content_agent.py:_build_prompt แต่ตัด brand context
ให้สั้นลงเพื่อวัดที่ "ความสามารถเขียน" ไม่ใช่ "ขนาด context"
"""
import json
import re
import subprocess
import sys
import time

MODELS = [
    "opencode/deepseek-v4.1-flash-free",
    "opencode/nemotron-3.5-lightning-free",
    "opencode/nemotron-3-ultra-free",
    "opencode/big-pickle",
    "opencode/mimo-v2.6-flash-free",
]
SECTIONS = ("## Hook", "## Body", "## CTA", "## Hashtags")
THAI = re.compile(r"[\u0e00-\u0e7f]")

PROMPT = """คุณคือ Content Creator (เสก) ของ SoloCorp OS
เขียน draft โพสต์ LinkedIn ภาษาไทย เป็น markdown ที่มีหัวข้อครบ 4 นี้เท่านั้น:
## Hook
## Body
## CTA
## Hashtags
ความยาวรวม 700-2000 ตัวอักษร ห้ามใส่คำอธิบายอื่นนอก 4 หัวข้อนี้

BRIEF: เล่าเรื่องที่ทีม AI 20 แผนกต้องมี certification 4 ด่าน เพราะเคยเจอเคส agent
รายงานว่า "งานเสร็จแล้ว" ทั้งที่ไม่มีโค้ดเปลี่ยนแม้แต่บรรทัดเดียว กลุ่มเป้าหมาย: founder
ที่กำลังสร้างทีม AI ของตัวเอง"""


def probe(model: str) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run(
            ["opencode", "run", "--agent", "plan", "--model", model],
            input=PROMPT, capture_output=True, text=True, timeout=180,
            cwd="/data/projects/Lab-solocorp-os2.4",
        )
        out = p.stdout.strip()
        err = p.stderr.strip()
        code = p.returncode
    except subprocess.TimeoutExpired:
        return {"model": model, "ok": False, "reason": "timeout(180s)"}
    secs = round(time.time() - t0, 1)

    missing = [s for s in SECTIONS if s not in out]
    thai_chars = len(THAI.findall(out))
    tool_attempt = "permission requested" in err or "→ Read" in err
    return {
        "model": model,
        "ok": code == 0 and bool(out) and not missing,
        "exit": code,
        "seconds": secs,
        "chars": len(out),
        "thai_chars": thai_chars,
        "sections_missing": missing,
        "tool_attempt": tool_attempt,
        "preview": out[:160].replace("\n", " ⏎ "),
    }


if __name__ == "__main__":
    rows = [probe(m) for m in MODELS]
    for r in rows:
        print(json.dumps(r, ensure_ascii=False), flush=True)
    ok = [r for r in rows if r.get("ok")]
    print(f"\n--- {len(ok)}/{len(rows)} ผ่านเกณฑ์ (ครบ 4 หัวข้อ + มีข้อความ) ---")
    if ok:
        best = min(ok, key=lambda r: r["seconds"])
        print(f"เร็วสุด: {best['model']} ({best['seconds']}s)")
        top = max(ok, key=lambda r: r["thai_chars"])
        print(f"เนื้อหาไทยมากสุด: {top['model']} ({top['thai_chars']} ตัวอักษรไทย)")
    sys.exit(0 if ok else 1)

#!/usr/bin/env python3
"""ตรวจคลิปในโฟลเดอร์ของ Owner เทียบเงื่อนไข X Video Kickstart Bonus

เงื่อนไข (Terms §4(a)):
  • แนวตั้ง 9:16
  • ความยาว < 3 นาที (180 วิ)
  • ไม่มีลายน้ำ/ชื่อ/โลโก้ของแพลตฟอร์มอื่น  (ต้องดูด้วยตา/ภาพ)
  • เป็นของครีเอเตอร์เอง

ใช้: python scripts/audit_clips.py <โฟลเดอร์> [--frames]
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_S = 180
TARGET_RATIO = 9 / 16
TOLERANCE = 0.02


def probe(path: Path) -> dict:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error",
             "-select_streams", "v:0",
             "-show_entries", "stream=width,height:format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(r.stdout or "{}")
        st = (data.get("streams") or [{}])[0]
        dur = float((data.get("format") or {}).get("duration") or 0)
        w, h = int(st.get("width") or 0), int(st.get("height") or 0)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    ratio = (w / h) if h else 0
    vertical = bool(h) and abs(ratio - TARGET_RATIO) < TOLERANCE
    short_enough = 0 < dur < MAX_S
    size_mb = path.stat().st_size / 1_048_576
    return {
        "ok": True, "width": w, "height": h, "ratio": round(ratio, 4),
        "duration_s": round(dur, 1), "size_mb": round(size_mb, 1),
        "vertical": vertical, "short_enough": short_enough,
        "qualifies": vertical and short_enough,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--frames", action="store_true", help="สร้างเฟรมตรวจลายน้ำ")
    ap.add_argument("--out", default="/tmp/opencode/clip_audit.json")
    args = ap.parse_args()

    folder = Path(args.folder).expanduser()
    vids = sorted(p for p in folder.glob("*")
                 if p.suffix.lower() in (".mp4", ".mov", ".webm", ".m4v"))
    print(f"พบ {len(vids)} ไฟล์วิดีโอใน {folder}\n")

    rows = []
    for p in vids:
        info = probe(p)
        info["file"] = p.name
        info["path"] = str(p)
        rows.append(info)
        if not info.get("ok"):
            mark = "⚠️ "
            detail = info.get("error", "")[:40]
        else:
            mark = "✅" if info["qualifies"] else "❌"
            detail = (f"{info['width']}x{info['height']} · {info['duration_s']}วิ · "
                      f"{info['size_mb']}MB")
        v = "9:16 ✅" if info.get("vertical") else (
            "ไม่ใช่ 9:16 ❌" if info.get("ok") else "?")
        s = "<3น. ✅" if info.get("short_enough") else (
            "ยาวเกิน 3น. ❌" if info.get("ok") else "?")
        print(f"{mark} {p.name[:48]:50} {detail:34} {v:14} {s}")

    good = [r for r in rows if r.get("qualifies")]
    print(f"\n{'='*70}")
    print(f"ผ่านเงื่อนไขขนาด+เวลา: {len(good)}/{len(rows)} คลิป")
    if len(good) >= 15:
        print(f"🎉 ครบ 15 คลิปแล้ว → พร้อมลุ้นโบนัส X Video Kickstart Bonus")
    elif good:
        print(f"⚠️ ขาดอีก {15 - len(good)} คลิป (นับวันตาม PT)")
    print("\n⚠️ ยังต้องตรวจด้วยตา: ไม่มีลายน้ำของแพลตฟอร์มอื่น / เป็นของครีเอเตอร์เอง / ไม่ใช่คลิปซ้ำ")

    if args.frames:
        out = Path("/tmp/opencode/frames")
        out.mkdir(parents=True, exist_ok=True)
        for r in good:
            stem = Path(r["file"]).stem
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", str(r["duration_s"] / 2),
                 "-i", r["path"], "-frames:v", "1",
                 "-vf", "scale=300:533", str(out / f"{stem}.png")],
                capture_output=True, timeout=60)
        print(f"\nเฟรมกลางคลิป → {out}")

    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(f"บันทึกรายงาน: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

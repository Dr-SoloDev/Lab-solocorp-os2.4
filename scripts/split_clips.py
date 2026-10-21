#!/usr/bin/env python3
"""split_clips.py — ตัดคลิปยาวเป็นท่อน ≤ 3 นาที (เงื่อนไข X Video Kickstart Bonus)

Terms §4(a): คลิปต้อง 9:16 และความยาว < 3 นาที
→ คลิปยาว 7-8 นาที ที่ถ่ายไว้แล้ว = ได้ 3 คลิปโบนัส

ใช้:
  python scripts/split_clips.py IN.mp4 --out-dir DIR [--max 179] [--out-prefix NAME]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def probe_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, timeout=60)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def probe_dims(path: Path) -> tuple[int, int]:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=60)
    try:
        w, h = (r.stdout or "0,0").strip().split(",")[:2]
        return int(w), int(h)
    except Exception:
        return 0, 0


def main() -> int:
    ap = argparse.ArgumentParser(description="ตัดคลิปยาวเป็นท่อน ≤ max วินาที")
    ap.add_argument("input")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--max", type=int, default=179,
                    help="ความยาวสูงสุดต่อท่อน (วินาที)")
    ap.add_argument("--out-prefix", default=None)
    ap.add_argument("--crf", type=int, default=20)
    args = ap.parse_args()

    src = Path(args.input)
    out_dir = Path(args.out_dir)
    if not src.exists():
        print(f"❌ ไม่พบไฟล์: {src}")
        return 1

    dur = probe_duration(src)
    w, h = probe_dims(src)
    if dur <= 0:
        print("❌ อ่านความยาวไม่ได้")
        return 1

    vertical = h and abs((w / h) - 9 / 16) < 0.02
    n = max(1, int(dur // args.max) + (1 if dur % args.max else 0))
    print(f"📂 {src.name}")
    print(f"   {w}x{h} · {dur:.1f}วิ · 9:16 {'✅' if vertical else '❌'}")
    print(f"   แบ่งเป็น {n} ท่อน (≤ {args.max} วิ)")

    if dur <= args.max:
        print("ℹ️ ไม่ต้องตัด (อยู่ในลิมิตแล้ว)")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.out_prefix or src.stem
    step = dur / n
    made = []
    for i in range(n):
        start = i * step
        length = min(step, dur - start)
        out = out_dir / f"{prefix}_part{i+1}.mp4"
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error",
             "-ss", f"{start:.3f}", "-i", str(src),
             "-t", f"{length:.3f}",
             "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
             "-movflags", "+faststart", str(out)],
            capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            print(f"❌ ท่อน {i+1} ล้ม: {(r.stderr or '')[-200:]}")
            continue
        made.append(out)
        print(f"   ✅ part{i+1}  {length:.0f}วิ  {out.stat().st_size/1_048_576:.1f}MB")

    print(f"\nได้ {len(made)} ท่อน → {out_dir}")
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main())

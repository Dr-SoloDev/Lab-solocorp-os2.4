#!/usr/bin/env python3
"""burn_subs.py — เบิร์นซับไทยลงวิดีโอ (9:16 สำหรับ X/TikTok)

ใช้: python scripts/burn_subs.py IN.mp4 --srt sub.srt --out OUT.mp4
     python scripts/burn_subs.py IN.mp4 --srt sub.srt --out OUT.mp4 --font "Noto Sans Thai" --size 13

ทำไมต้องมี: คลิปของครีเอเตอร์ออกเสียงคำอังกฤษเป็นเสียงไทย ("prompt"→"พร้อม")
→ คนดูไทยฟังไม่ออก ต้องมีซับ (แก้ปัญหาโดยไม่ต้องถ่ายใหม่)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

FONT_DEFAULT = "Noto Sans Thai"
# ขนาดฟอนต์ในหน่วยของ libass (PlayResY 288) → 11 ≈ 73px ที่ 1920
SIZE_DEFAULT = 11


def main() -> int:
    ap = argparse.ArgumentParser(description="เบิร์นซับไทยลงวิดีโอ")
    ap.add_argument("input")
    ap.add_argument("--srt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--font", default=FONT_DEFAULT)
    ap.add_argument("--size", type=int, default=SIZE_DEFAULT)
    ap.add_argument("--margin-v", type=int, default=60,
                    help="ระยะจากขอบล่าง (หน่วย libass)")
    ap.add_argument("--crf", type=int, default=20)
    args = ap.parse_args()

    src = Path(args.input)
    srt = Path(args.srt)
    out = Path(args.out)
    if not src.exists():
        print(f"❌ ไม่พบไฟล์: {src}")
        return 1
    if not srt.exists():
        print(f"❌ ไม่พบ SRT: {srt}")
        return 1
    if not shutil.which("ffmpeg"):
        print("❌ ไม่พบ ffmpeg")
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)

    # ── ทำความสะอาด SRT ──
    # transcribe.py เขียนหัวไฟล์เป็น markdown ("# transcript (...)") ซึ่งไม่ใช่ SRT
    # → libass อ่านไม่ได้ ("Unable to open") → ตัดหัวออกแล้วเขียนเป็นไฟล์ชั่วคราว
    raw = srt.read_text(encoding="utf-8")
    lines = [ln for ln in raw.splitlines()
             if not ln.lstrip().startswith("#")]
    # ตัดบรรทัดว่างหัว
    while lines and not lines[0].strip():
        lines.pop(0)
    cleaned = "\n".join(lines).strip() + "\n"
    tmp_srt = out.parent / f".{out.stem}.clean.srt"
    tmp_srt.write_text(cleaned, encoding="utf-8")

    # libass ต้อง path escape
    srt_arg = str(tmp_srt.resolve()).replace(":", r"\:").replace("'", r"\'")
    style = (f"FontName={args.font},FontSize={args.size},"
             f"PrimaryColour=&H00FFFFFF,OutlineColour=&HC0000000,BorderStyle=3,"
             f"Outline=2,Shadow=0,MarginV={args.margin_v},Alignment=2")

    vf = f"subtitles='{srt_arg}':force_style='{style}'"
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(src),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        str(out),
    ]
    print(f"🎬 เบิร์นซับ → {out.name}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        print(f"❌ ล้มเหลว: {(r.stderr or '')[-500:]}")
        return 1

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-show_entries", "format=duration",
         "-of", "default=nw=1", str(out)],
        capture_output=True, text=True, timeout=60)
    tmp_srt.unlink(missing_ok=True)
    print(f"✅ เสร็จ · {out.stat().st_size/1_048_576:.1f} MB")
    print(probe.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())

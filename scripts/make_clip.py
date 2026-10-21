#!/usr/bin/env python3
"""🎬 make_clip.py — สคริปต์ → คลิปแนวตั้ง 9:16 พร้อมเสียงพูดไทย + ซับไตเติล

ทำงานร่วมกับ `solocorp_skills/creator.py` (4 ท่อน → script.md) และ
`solocorp_skills/programs/x_kickstart.py` (เงื่อนไข 9:16 / <3 นาที)

สายผลิต (ทั้งหมด local ไม่ต้องใช้ key):
  • เสียงพูด  → piper (th_TH-tsync2-medium) + tltk สำหรับหันศัลย์ไทย
  • ซับไตเติล → ffmpeg + libass (ฟอนต์ Noto Sans Thai)
  • ภาพ        → แนวตั้ง 1080x1920 (preset "reels")

ใช้:
  python scripts/make_clip.py --script bus/media/creator/<slug>/<วัน>/xxx.script.md \\
      --out bus/media/creator/<slug>/<วัน>/xxx.mp4
  python scripts/make_clip.py --script ... --out ... --bg 0x1a1a2e
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TTS_VENV = Path("/data/venvs/tts/bin/python")
PIPER_MODEL = Path("/data/models/piper/th_TH-tsync2-medium.onnx")
PIPER_CONFIG = Path("/data/models/piper/th_TH-tsync2-medium.onnx.json")

FONT = "Noto Sans Thai"
SIZES = {"reels": (1080, 1920), "master": (1920, 1080)}


# ══════════════════════════════════════════════════════════════════════
# อ่าน script.md → ท่อน
# ══════════════════════════════════════════════════════════════════════


def parse_script(path: Path) -> list[dict[str, str]]:
    """ดึงท่อนจากตาราง markdown ของ script.md

    | # | ท่อน | เวลา | บท |
    | 1 | hook | 0–3 วิ | ข้อความ... |
    """
    beats: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 4 or not cols[0].isdigit():
            continue
        text = cols[3].strip()
        if not text:
            continue
        beats.append({"n": cols[0], "label": cols[1], "time": cols[2], "text": text})
    return beats


# ══════════════════════════════════════════════════════════════════════
# เสียงพูด (piper)
# ══════════════════════════════════════════════════════════════════════


def tts(text: str, out_wav: Path) -> float:
    """สังเคราะห์เสียงไทย → wav — คืนความยาว (วินาที)"""
    if not TTS_VENV.exists() or not PIPER_MODEL.exists():
        raise RuntimeError(
            "ยังไม่มีเสียงพูดไทย — ต้องมี /data/venvs/tts และ /data/models/piper/th_TH-tsync2-medium.onnx"
        )
    code = (
        "import wave, numpy as np, sys\n"
        "from piper import PiperVoice\n"
        "v = PiperVoice.load(sys.argv[1], config_path=sys.argv[2])\n"
        "chunks = list(v.synthesize(sys.argv[3]))\n"
        "arr = np.concatenate([c.audio_float_array for c in chunks])\n"
        "sr = chunks[0].sample_rate\n"
        "with wave.open(sys.argv[4],'wb') as w:\n"
        "    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)\n"
        "    w.writeframes((np.clip(arr,-1,1)*32767).astype(np.int16).tobytes())\n"
        "print(sr)\n"
    )
    r = subprocess.run(
        [str(TTS_VENV), "-c", code, str(PIPER_MODEL), str(PIPER_CONFIG),
         text, str(out_wav)],
        capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0 or not out_wav.exists() or out_wav.stat().st_size == 0:
        raise RuntimeError(f"TTS ล้มเหลว: {(r.stderr or '')[-300:]}")
    with wave.open(str(out_wav), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def wrap_text(text: str, width: int = 30, max_lines: int = 3) -> str:
    """ตัดบรรทัดไทยให้พอดีความกว้างจอ (libass ไม่ wrap ให้เอง)"""
    import textwrap
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return ""
    lines = textwrap.wrap(clean, width=width) or [clean]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:width - 1].rstrip() + "…"
    # escape ให้ถูก ASS: { } และขึ้นบรรทัดใหม่
    out = []
    for ln in lines:
        ln = ln.replace("{", "(").replace("}", ")")
        out.append(ln)
    return "\\N".join(out)


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ══════════════════════════════════════════════════════════════════════
# ประกอบคลิป
# ══════════════════════════════════════════════════════════════════════


def make_segment(wav: Path, srt: Path, out_mp4: Path, size: tuple[int, int],
                 bg: str, fps: int = 25) -> None:
    """ท่อนหนึ่ง: พื้นหลังสี + ซับไตเติล + เสียงพูด"""
    w, h = size
    vf = (
        f"subtitles={srt}:force_style='FontName={FONT},FontSize=11,"
        f"PrimaryColour=&H00FFFFFF,OutlineColour=&H99000000,BorderStyle=3,"
        f"Outline=2,Shadow=0,MarginV=40,MarginL=60,MarginR=60,Alignment=2'"
    )
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", f"color=c={bg}:s={w}x{h}:r={fps}",
         "-i", str(wav),
         "-vf", vf,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
         "-shortest", str(out_mp4)],
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ทำท่อนวิดีโอล้มเหลว: {(r.stderr or '')[-400:]}")


def concat(segments: list[Path], out_mp4: Path, size: tuple[int, int]) -> None:
    """ต่อท่อนเข้าด้วย concat demuxer"""
    w, h = size
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        for s in segments:
            fh.write(f"file '{s.resolve()}'\n")
        list_file = Path(fh.name)
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", str(list_file),
             "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                     f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
             "-c:a", "aac", "-b:a", "128k",
             "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
             str(out_mp4)],
            capture_output=True, text=True, timeout=900,
        )
        if r.returncode != 0:
            raise RuntimeError(f"ต่อคลิปล้มเหลว: {(r.stderr or '')[-400:]}")
    finally:
        list_file.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="สคริปต์ → คลิปแนวตั้งพร้อมเสียงไทย")
    ap.add_argument("--script", required=True, help="พาธไฟล์ script.md")
    ap.add_argument("--out", required=True, help="พาธไฟล์ .mp4 ที่จะได้")
    ap.add_argument("--preset", default="reels", choices=list(SIZES), help="reels=9:16")
    ap.add_argument("--bg", default="0x14121f", help="สีพื้นหลัง")
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--dry-run", action="store_true", help="แค่แสดงแผน ไม่ทำ")
    args = ap.parse_args()

    script = Path(args.script)
    out = Path(args.out)
    size = SIZES[args.preset]

    if not script.exists():
        print(f"❌ ไม่พบไฟล์สคริปต์: {script}")
        return 1

    beats = parse_script(script)
    if not beats:
        print(f"❌ อ่านท่อนจาก {script} ไม่ได้ (ตารางไม่ตรงรูปแบบ)")
        return 1

    print(f"📜 {script.name} → {len(beats)} ท่อน · {size[0]}x{size[1]}")
    for b in beats:
        print(f"   {b['n']}. {b['label']:18} {b['time']:10} {b['text'][:46]}")

    if args.dry_run:
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="makeclip-"))
    segments: list[Path] = []
    total = 0.0

    try:
        for i, b in enumerate(beats, 1):
            wav = tmp / f"seg{i}.wav"
            dur = tts(b["text"], wav)
            total += dur
            srt = tmp / f"seg{i}.srt"
            srt.write_text(
                f"1\n00:00:00,000 --> {srt_time(dur)}\n{wrap_text(b['text'])}\n",
                encoding="utf-8")
            seg = tmp / f"seg{i}.mp4"
            make_segment(wav, srt, seg, size, args.bg, args.fps)
            segments.append(seg)
            print(f"   ✅ ท่อน {i}: {dur:.1f}s")

        concat(segments, out, size)
        size_mb = out.stat().st_size / 1_048_576
        print(f"🎬 เสร็จ: {out} ({size_mb:.1f} MB · {total:.1f}s)")

        # ตรวจเงื่อนไขโปรแกรมให้อัตโนมัติ
        try:
            sys.path.insert(0, str(ROOT))
            from solocorp_skills.programs.x_kickstart import check_video
            for c in check_video(out):
                mark = "✅" if c["ok"] else "❌"
                print(f"   {mark} {c['rule']} — {c['detail']}")
        except Exception as e:
            print(f"   (ตรวจเงื่อนไขไม่ได้: {e})")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

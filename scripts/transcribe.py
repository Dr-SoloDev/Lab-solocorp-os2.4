#!/data/venvs/speech/bin/python
"""🎧 transcribe.py — SoloCorp OS media ears (ถอดเทป/สรุปคลิป)

ใช้ faster-whisper (local, ไม่เสีย key นอก) ผ่าน venv ถาวร /data/venvs/speech

ใช้:
  scripts/transcribe.py IN.mp4 [--model base] [--lang th] [--out transcript.txt] [--srt]
  scripts/transcribe.py IN.mp3 --model small --lang auto

Models: tiny (ไว) / base (default, สมดุล) / small (ชัดสุด) — โหลดครั้งแรกครั้งเดียว
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}


def to_wav(src: Path) -> tuple[Path, tempfile.TemporaryDirectory | None]:
    if src.suffix.lower() in AUDIO_EXTS:
        return src, None
    tmp = tempfile.TemporaryDirectory(prefix="solocorp-media-")
    out = Path(tmp.name) / "audio.wav"
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(src),
         "-vn", "-ac", "1", "-ar", "16000", str(out)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"ffmpeg แปลงเสียงล้มเหลว: {r.stderr[:300]}")
    return out, tmp


def main() -> None:
    ap = argparse.ArgumentParser(prog="transcribe",
                                 description="ถอดเทปเสียง/วิดีโอ (local Whisper)")
    ap.add_argument("input", help="ไฟล์เสียงหรือวิดีโอ")
    ap.add_argument("--model", default="base",
                    choices=["tiny", "base", "small"],
                    help="tiny=ไว / base=สมดุล (default) / small=ชัดสุด")
    ap.add_argument("--lang", default="auto",
                    help="รหัสภาษา (เช่น th, en) หรือ auto (default)")
    ap.add_argument("--out", default="",
                    help="ไฟล์ผลลัพธ์ (default: พิมพ์ stdout)")
    ap.add_argument("--srt", action="store_true",
                    help="ออกเป็น SRT แทน plain text")
    args = ap.parse_args()

    from faster_whisper import WhisperModel

    src = Path(args.input)
    if not src.exists():
        sys.exit(f"❌ ไม่เจอไฟล์: {src}")
    wav, tmp = to_wav(src)
    try:
        model = WhisperModel(args.model, device="cpu", compute_type="int8")
        segs, info = model.transcribe(
            str(wav),
            language=None if args.lang == "auto" else args.lang,
        )
        lang = info.language
        lines: list[str] = []
        for s in segs:
            if args.srt:
                def ts(t: float) -> str:
                    h, r = divmod(t, 3600)
                    m, sec = divmod(r, 60)
                    return f"{int(h):02}:{int(m):02}:{sec:06.3f}".replace(".", ",")
                lines.append(f"{len(lines)+1}\n{ts(s.start)} --> {ts(s.end)}\n{s.text.strip()}\n")
            else:
                lines.append(f"[{s.start:.1f}-{s.end:.1f}] {s.text.strip()}")
        head = f"# transcript ({src.name} | lang={lang} | model={args.model})\n\n"
        result = head + "\n".join(lines) + "\n"
    finally:
        if tmp is not None:
            tmp.cleanup()

    if args.out:
        Path(args.out).write_text(result, encoding="utf-8")
        print(f"✅ เขียนแล้ว: {args.out}")
    else:
        print(result)


if __name__ == "__main__":
    main()

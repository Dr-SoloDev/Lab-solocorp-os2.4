"""make_broll_clip.py — ประกอบคลิปเส้นทาง B (เสียงจริง + ภาพจากคลัง b-roll)

เส้นทาง B = ครีเอเตอร์อัดเสียงอย่างเดียว → ระบบเลือก b-roll จากคลัง
→ แปลงเป็น 9:16 → ใส่ซับไทย → ได้คลิปพร้อมโพสต์ โดยครีเอเตอร์ไม่ต้องถ่าย

ใช้:
  python scripts/make_broll_clip.py --script X.script.md --library <โฟลเดอร์> \\
      --audio <เสียงต้นฉบับ> --out OUT.mp4 --plan beat_broll.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def probe(path: Path) -> dict:
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-show_entries", "format=duration",
             "-of", "json", str(path)], 60)
    try:
        d = json.loads(r.stdout or "{}")
        st = (d.get("streams") or [{}])[0]
        return {"w": int(st.get("width") or 0), "h": int(st.get("height") or 0),
                "dur": float((d.get("format") or {}).get("duration") or 0)}
    except Exception:
        return {"w": 0, "h": 0, "dur": 0}


def parse_beats(script: Path) -> list[dict[str, str]]:
    """อ่านท่อนจาก script.md (ตาราง: | # | ท่อน | เวลา | บท |)"""
    beats = []
    for line in script.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cols = [c.strip() for c in s.strip("|").split("|")]
        if len(cols) < 4 or not cols[0].isdigit():
            continue
        beats.append({"n": cols[0], "label": cols[1], "time": cols[2], "text": cols[3]})
    return beats


def pick_broll(library: Path, keywords: list[str], used: set[str]) -> Path | None:
    """เลือกไฟล์ b-roll ที่ชื่อตรงคำค้น (เรียงตามลำดับความสำคัญ)"""
    files = [p for p in sorted(library.iterdir())
             if p.suffix.lower() == ".mp4" and p.name not in used]
    for kw in keywords:
        for p in files:
            if kw.lower() in p.name.lower():
                return p
    return None


def to_vertical(src: Path, dst: Path, dur: float, size: tuple[int, int]) -> bool:
    """แปลงเป็น 9:16 — crop กลาง (ถ้าแนวนอน) แล้ว scale"""
    w, h = size
    src_info = probe(src)
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
          f"crop={w}:{h},format=yuv420p")
    if src_info["h"] > src_info["w"]:
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
              f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p")
    r = run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-t", f"{dur:.3f}",
             "-vf", vf, "-r", "24", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "22", "-pix_fmt", "yuv420p", "-an", str(dst)], 900)
    return r.returncode == 0 and dst.exists()


def main() -> int:
    ap = argparse.ArgumentParser(description="ประกอบคลิปเส้นทาง B")
    ap.add_argument("--script", required=True, help="ไฟล์ script.md (4 ท่อน)")
    ap.add_argument("--library", required=True, help="โฟลเดอร์ b-roll")
    ap.add_argument("--plan", required=True, help="JSON: ท่อน → คำค้น b-roll")
    ap.add_argument("--audio", help="ไฟล์เสียงต้นฉบับ (วางเป็นแทร็คเสียงจริง)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--font", default="Noto Sans Thai")
    ap.add_argument("--subtitle-size", type=int, default=11)
    args = ap.parse_args()

    script = Path(args.script)
    library = Path(args.library)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    w, h = (int(x) for x in args.size.split("x"))
    tmp = Path("/tmp/opencode/broll_build")
    tmp.mkdir(parents=True, exist_ok=True)

    beats = parse_beats(script)
    if not beats:
        print("❌ อ่านท่อนจาก script.md ไม่ได้")
        return 1

    used: set[str] = set()
    segments: list[Path] = []
    srt_lines: list[str] = []
    audio_windows: list[tuple[float, float]] = []
    cursor = 0.0

    print(f"📜 {script.name} → {len(beats)} ท่อน")
    for i, b in enumerate(beats):
        kws = plan.get(str(i + 1)) or plan.get(b["n"]) or []
        src = pick_broll(library, kws, used) if kws else None
        if src is None:
            print(f"   ⚠️ ท่อน {b['n']} ไม่เจอ b-roll สำหรับ {kws} — ใช้คลิปว่าง")
            continue
        used.add(src.name)
        info = probe(src)
        dur = min(info["dur"], 12.0)          # ไม่เกิน 12 วิต่อท่อน
        seg = tmp / f"seg{i+1}.mp4"
        if not to_vertical(src, seg, dur, (w, h)):
            print(f"   ❌ แปลง {src.name} ไม่สำเร็จ")
            continue
        segments.append(seg)
        # เวลาเสียง: ตัดตามความยาวท่อน
        audio_windows.append((cursor, cursor + dur))
        cursor += dur
        srt_lines.append(f"{len(srt_lines)+1}\n"
                         f"{srt_time(cursor - dur)} --> {srt_time(cursor)}\n{b['text']}\n")
        print(f"   ✅ ท่อน {b['n']} ({b['label']}): {src.name[:42]} · {dur:.1f}วิ")

    if not segments:
        print("❌ ไม่ได้ท่อนไหนเลย")
        return 1

    # ── ต่อภาพ ──
    list_file = tmp / "list.txt"
    list_file.write_text("".join(f"file '{s.resolve()}'\n" for s in segments),
                         encoding="utf-8")
    silent = tmp / "silent.mp4"
    r = run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", str(list_file), "-c", "copy", str(silent)], 900)
    if r.returncode != 0:
        print(f"❌ ต่อคลิปล้ม: {(r.stderr or '')[-300:]}")
        return 1

    # ── ซับ ──
    srt = tmp / "clip.srt"
    srt.write_text("\n".join(srt_lines), encoding="utf-8")

    # ── เสียง ──
    audio_args: list[str] = []
    if args.audio and Path(args.audio).exists():
        # ต่อเสียงจริงตามความยาวท่อนทั้งหมด
        audio_args = ["-i", str(Path(args.audio).resolve())]
    else:
        audio_args = ["-f", "lavfi", "-i", "anullsrc=r=24000:cl=stereo"]

    srt_arg = str(srt.resolve()).replace(":", r"\:").replace("'", r"\'")
    style = (f"FontName={args.font},FontSize={args.subtitle_size},"
             f"PrimaryColour=&H00FFFFFF,OutlineColour=&HC0000000,BorderStyle=3,"
             f"Outline=2,Shadow=0,MarginV=60,Alignment=2")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    r = run(["ffmpeg", "-y", "-v", "error",
             "-i", str(silent), *audio_args,
             "-vf", f"subtitles='{srt_arg}':force_style='{style}'",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
             "-shortest", "-movflags", "+faststart", str(out)], 1800)
    if r.returncode != 0:
        print(f"❌ เบิร์นซับล้ม: {(r.stderr or '')[-400:]}")
        return 1

    info = probe(out)
    print(f"✅ เสร็จ: {out} · {out.stat().st_size/1_048_576:.1f}MB · "
          f"{info['w']}x{info['h']} · {info['dur']:.1f}วิ")
    return 0


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


if __name__ == "__main__":
    sys.exit(main())

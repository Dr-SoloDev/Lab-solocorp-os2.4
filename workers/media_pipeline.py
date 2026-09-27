#!/usr/bin/env python3
"""🎬 media_pipeline.py — SoloCorp OS Media Pipeline (Phase 1: ไม่ใช้ Pro)

Forum 005 → Owner เคาะ pilot EP.4 ก่อน → เฟสนี้ใช้ของฟรีทั้งหมด:
  ingest (repo → brief) → script (ซอยท่อน 10 วิ + timestamp) →
  titles (หัวข้อ+hashtag) → concat (ffmpeg) → cover (SVG)

Gate: สคริปทุกตอนต้องผ่าน Owner review ก่อนเจน (ไม่เผาเครดิต)

ใช้:
  python -m workers.media_pipeline ingest --out bus/media/ep4/brief.md
  python -m workers.media_pipeline script --brief bus/media/ep4/brief.md \
      --topic "EP.4: Turbo — CEO Robot" --total 180 --seg 10 --out bus/media/ep4/scripts.md
  python -m workers.media_pipeline titles --brief ... --topic ... --out bus/media/ep4/titles.md
  python -m workers.media_pipeline concat --list clips.txt --out master.mp4
  python -m workers.media_pipeline cover --title "EP.4 ..." --out cover.svg
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

MEDIA_DIR = REPO_ROOT / "bus" / "media"

SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".codegraph",
             "loop_runner", ".main.lock"}
SKIP_SUFFIX = (".pyc", ".pid", ".lock")
KEY_DOCS = ["AGENTS.md", "CLAUDE.md", "docs/ARCHITECTURE.md", "bus/plans/forum-room-port.md"]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def collect_repo_snapshot(max_files: int = 120, max_chars: int = 12000) -> str:
    files: list[str] = []
    for p in sorted(REPO_ROOT.rglob("*")):
        if len(files) >= max_files:
            break
        try:
            rel = p.relative_to(REPO_ROOT)
        except ValueError:
            continue
        if any(part in SKIP_DIRS or part.startswith("test_") or part.startswith("tmp_")
               for part in rel.parts):
            continue
        if p.is_file() and not p.suffix in SKIP_SUFFIX and not p.name.startswith(("test_", "tmp_", "run_", "check_", "poll_", "cron_", "bus_")):
            files.append(str(rel))
    doc_text = ""
    for d in KEY_DOCS:
        f = REPO_ROOT / d
        if f.exists():
            doc_text += f"\n\n===== {d} =====\n" + f.read_text(encoding="utf-8")[:3000]
    snap = f"FILES ({len(files)}):\n" + "\n".join(files[:max_files])
    return (snap + doc_text)[:max_chars]


async def llm(prompt: str, max_tokens: int = 2000) -> str:
    from workers.llm_provider import think
    return await think(prompt, max_tokens=max_tokens)


def cmd_ingest(out: str) -> None:
    snap = collect_repo_snapshot()
    brief = asyncio.run(llm(
        "You are a documentary researcher. Source material from SoloCorp OS repo:\n"
        f"{snap}\n\nWrite a production brief in Thai (max 30 lines): "
        "1) SoloCorp OS คืออะไร 2) ตัวละครหลัก (Owner/CEO Turbo/CFO meetoo/CMO Mark/Architect/ทีม) "
        "3) 3 plot threads ที่น่าเล่าเป็น EP ต่อไป",
        max_tokens=1500,
    ))
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# Production Brief ({now_iso()})\n\n{brief}\n", encoding="utf-8")
    print(f"✅ brief: {p}")


SEG_WORD_LIMIT = 32  # คำพูดไทยสูงสุดต่อท่อน 10 วิ (พูดทัน)

MODES = {
    "cinematic": "หลายฉาก cinematic เปลี่ยนโลเคชันได้ (แพง: ต้องมี character ref)",
    "static": "ฉากเดียว static: พิธีกรนั่งโต๊ะหน้าโต๊ะทำงานหลังจอคอม (ถูก: หน้าตัวละครคงที่เอง)",
}


def cmd_script(brief: str, topic: str, total: int, seg: int, out: str,
               mode: str = "cinematic", count: int = 0) -> None:
    n = count or total // seg
    pilot = (f"PILOT MODE: write ONLY segments 1..{n} then STOP. "
             f"Do NOT write segment {n + 1} or beyond. " if count else "")
    brief_text = Path(brief).read_text(encoding="utf-8")
    scripts = asyncio.run(llm(
        "You are a video scriptwriter for SoloCorp OS series.\n"
        f"KNOWLEDGE:\n{brief_text[:4000]}\n\n"
        f"Write EXACTLY {n} numbered Thai scripts for: {topic}\n{pilot}"
        f"Mode: {mode} — {MODES[mode]}. "
        f"Total {total}s, {seg}s per segment. Format per segment (all 6 fields):\n"
        f"[ท่อน i/MM:SS-MM:SS] พูด: (≤{SEG_WORD_LIMIT} คำ, ภาษาพูด) + "
        "| ฉาก: (ท่าทาง) + | กราฟิก: (popup text) + | SFX: (เสียง) + "
        "| ภาพ: (visual direction) + [ไฟล์อ้างอิง]\n"
        "Rules: every factual claim ends with [source file]; no intro/outro outside "
        "segments; last segment ends with cliffhanger.",
        max_tokens=3000,
    ))
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# Scripts: {topic} ({total}s / {n}×{seg}s / {mode} — รอ Owner review gate)\n\n{scripts}\n",
                 encoding="utf-8")
    print(f"✅ scripts: {p} (target {n} segments)")
    rep = cmd_validate(str(p), seg, write=False)
    print(rep)


def cmd_validate(path: str, seg: int = 10, write: bool = True) -> str:
    """ตรวจสคริป: นับท่อน, เลขเวลา, จำนวนคำ/ท่อน, ตัด citation [1] ออก"""
    import re
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    # ตัด citation ลอยของ Notebook [1] ก่อนส่งเจน
    text = re.sub(r"\[(?:\d+)(?:,\d+)*\]", "", text)
    heads = re.findall(r"\[ท่อน\s*(\d+)/(\d+):(\d+)-(\d+):(\d+)\]", text)
    issues: list[str] = []
    durs: list[int] = []
    for i, h in enumerate(heads, 1):
        idx, m1, s1, m2, s2 = map(int, h)
        if idx != i:
            issues.append(f"เลขท่อนผิด: เจอ {idx} ควรเป็น {i}")
        dur = (m2 * 60 + s2) - (m1 * 60 + s1)
        durs.append(dur)
        if dur <= 0 or dur > seg:
            issues.append(f"ท่อน {idx} ยาว {dur}s (กรอบ 1-{seg}s)")
        elif i == len(heads) and dur != seg:
            pass  # ท่อนสุดท้ายสั้นกว่าได้ (เช่น 8s outro)
    bodies = re.split(r"\[ท่อน\s*\d+/[^\]]+\]", text)[1:]
    for i, b in enumerate(bodies, 1):
        m = re.search(r"พูด:\s*(.+?)(?:\||$)", b, re.S)
        if m and len(m.group(1).split()) > SEG_WORD_LIMIT:
            issues.append(f"ท่อน {i} พูด {len(m.group(1).split())} คำ (> {SEG_WORD_LIMIT}) — พูดไม่ทัน")
    total = sum(durs)
    rep = (f"📋 validate {p.name}: {len(heads)} ท่อน / รวม {total}s "
           f"({'✅ ผ่าน' if not issues else '❌ ' + '; '.join(issues)}), "
           f"citation ลอยถูกตัดแล้ว")
    if write:
        print(rep)
    return rep


def cmd_titles(brief: str, topic: str, out: str) -> None:
    brief_text = Path(brief).read_text(encoding="utf-8")
    titles = asyncio.run(llm(
        "You are CMO of SoloCorp OS.\n"
        f"KNOWLEDGE:\n{brief_text[:2000]}\n\nFor video: {topic}\n"
        "Write in Thai: 3 title variants (hook-first, <60 chars) + 1 description (3 lines) "
        "+ hashtag set (8) + thumbnail text (4 words max).",
        max_tokens=800,
    ))
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# Titles: {topic}\n\n{titles}\n", encoding="utf-8")
    print(f"✅ titles: {p}")


RENDER_CONTRACT = {
    # master 16:9 + vertical สำหรับ Reels/TikTok (engineering render contract)
    "master": ("1920:1080", "5M"),
    "reels": ("1080:1920", "5M"),
}


def cmd_concat(lst: str, out: str, preset: str = "master") -> None:
    size, vbit = RENDER_CONTRACT.get(preset, RENDER_CONTRACT["master"])
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", lst, "-vf", f"scale={size}:force_original_aspect_ratio=decrease,"
         f"pad={size}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
         "-c:v", "libx264", "-b:v", vbit, "-c:a", "aac",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", out],
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        raise RuntimeError(f"concat ล้มเหลว: {r.stderr[:300]}")
    print(f"✅ master ({preset} {size}): {out}")


def cmd_cover(title: str, out: str) -> None:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#0a1628"/><stop offset="1" stop-color="#123a6d"/>
</linearGradient></defs>
<rect width="1920" height="1080" fill="url(#bg)"/>
<text x="960" y="480" font-family="sans-serif" font-size="120" font-weight="bold" fill="#ffb347" text-anchor="middle">{title}</text>
<text x="960" y="620" font-family="sans-serif" font-size="64" fill="#7fd4ff" text-anchor="middle">SoloCorp OS</text>
</svg>
"""
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(svg, encoding="utf-8")
    print(f"✅ cover: {p}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="media_pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ingest"); a.add_argument("--out", required=True)
    s = sub.add_parser("script"); s.add_argument("--brief", required=True)
    s.add_argument("--topic", required=True); s.add_argument("--total", type=int, default=180)
    s.add_argument("--seg", type=int, default=10); s.add_argument("--out", required=True)
    s.add_argument("--mode", choices=["cinematic", "static"], default="cinematic")
    s.add_argument("--count", type=int, default=0,
                   help="เจนแค่ K ท่อนแรก (pilot-clip-first: Owner เคาะแล้วค่อย batch)")
    v2 = sub.add_parser("validate"); v2.add_argument("--path", required=True)
    v2.add_argument("--seg", type=int, default=10)
    t = sub.add_parser("titles"); t.add_argument("--brief", required=True)
    t.add_argument("--topic", required=True); t.add_argument("--out", required=True)
    c = sub.add_parser("concat"); c.add_argument("--list", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--preset", choices=["master", "reels"], default="master")
    v = sub.add_parser("cover"); v.add_argument("--title", required=True)
    v.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "ingest":
        cmd_ingest(args.out)
    elif args.cmd == "script":
        cmd_script(args.brief, args.topic, args.total, args.seg, args.out,
                   args.mode, args.count)
    elif args.cmd == "validate":
        cmd_validate(args.path, args.seg)
    elif args.cmd == "titles":
        cmd_titles(args.brief, args.topic, args.out)
    elif args.cmd == "concat":
        cmd_concat(args.list, args.out, args.preset)
    elif args.cmd == "cover":
        cmd_cover(args.title, args.out)


if __name__ == "__main__":
    main()

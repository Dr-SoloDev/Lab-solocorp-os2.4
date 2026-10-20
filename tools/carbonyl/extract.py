#!/usr/bin/env python3
"""แปลง raw ANSI stream ของ carbonyl ให้เป็นข้อความอ่านได้

Carbonyl เป็นเบราว์เซอร์ที่วาดลงเทอร์มินัลจริง (ภาพ + ตัวอักษร) จึงไม่มี
"โหมดดึงข้อความ" เหมือน headless browser ทั่วไป — ต้องจำลองเทอร์มินัล
เพื่อรู้ว่าอักขระตัวไหนอยู่ที่ (row, col) ไหน แล้วค่อยอ่านทีละบรรทัด

ใช้:  carbonyl <url> | python3 extract.py
      python3 extract.py --raw < raw.txt
"""
from __future__ import annotations

import json
import re
import sys

# อักขระกราฟิก/บล็อกที่เป็น "พื้นหลังเชิงภาพ" — ไม่มีความหมายเชิงข้อความ
BLOCKS = re.compile(r"[▀-▟░-▓█▁-▇ ]")
ANSI_OSC = re.compile(r"\x1b\][0-9];([^\x07\x1b]*)(?:\x07|\x1b\\)")
ANSI_CSI = re.compile(r"\x1b\[([0-9;?]*)([a-zA-Z])")

# โต๊ะเก็บอักขระ: (row, col) -> char
screen: dict[tuple[int, int], str] = {}
row = col = 1
title = ""


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def handle_csi(params: str, final: str) -> None:
    """จัดการ escape sequence ชุดที่ใช้จริงใน carbonyl"""
    global row, col
    if params.startswith("?"):
        return  # DEC private mode (1049h, 1003h, ...) — ไม่กระทบตำแหน่ง
    nums = [int(p) for p in params.split(";") if p.isdigit()] if params else []

    if final == "H" or final == "f":  # cursor position
        r = nums[0] if len(nums) > 0 else 1
        c = nums[1] if len(nums) > 1 else 1
        row, col = max(1, r), max(1, c)
    elif final == "A":
        row -= nums[0] if nums else 1
    elif final == "B":
        row += nums[0] if nums else 1
    elif final == "C":
        col += nums[0] if nums else 1
    elif final == "D":
        col -= nums[0] if nums else 1
    elif final == "G":
        col = nums[0] if nums else 1
    elif final == "J":  # erase display
        mode = nums[0] if nums else 0
        if mode == 2:
            screen.clear()
    elif final == "K":  # erase line
        for (r, c) in list(screen):
            if r == row and c >= col:
                del screen[(r, c)]
    # 'm' (SGR / สี) และอื่น ๆ → ไม่ต้องทำอะไร เพราะเราเก็บแค่ตัวอักษร


def feed(text: str) -> None:
    """ป้อนข้อความ (มี escape ปนอยู่) เข้าเทอร์มินัลจำลอง"""
    global row, col
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\x1b":
            m = ANSI_CSI.match(text, i)
            if m:
                handle_csi(m.group(1), m.group(2))
                i = m.end()
                continue
            m = ANSI_OSC.match(text, i)
            if m:
                global title
                title = m.group(1) or title
                i = m.end()
                continue
            i += 1
            continue
        if ch == "\n":
            row += 1
            i += 1
            continue
        if ch == "\r":
            col = 1
            i += 1
            continue
        if ord(ch) < 32:
            i += 1
            continue
        screen[(row, col)] = ch
        col += 1
        i += 1


def build_lines() -> list[str]:
    if not screen:
        return []
    max_row = max(r for r, _ in screen)
    lines = []
    for r in range(1, max_row + 1):
        cols = [c for (rr, c) in screen if rr == r]
        if not cols:
            lines.append("")
            continue
        lo, hi = min(cols), max(cols)
        lines.append("".join(screen.get((r, c), " ") for c in range(lo, hi + 1)))
    return lines


def clean(lines: list[str]) -> str:
    out = []
    for line in lines:
        line = BLOCKS.sub("", line)
        # เศษจากการ kill process — ข้อความจาก shell อาจโผล่กลางบรรทัดได้
        # (ใช้ ASCII boundary เพราะ \b ใน Python ไม่แยกเลยไทยกับอังกฤษ)
        line = re.sub(r"(?<![A-Za-z])(Killed|Terminated|Aborted)(?![A-Za-z])", "", line)
        line = re.sub(r"[ \t]+", " ", line).strip()
        if not line:
            continue
        out.append(line)
    # ตัดบรรทัดซ้ำติดกัน (carbonyl วาดทับหลายรอบ → เกิดข้อความซ้ำ)
    deduped: list[str] = []
    for line in out:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return "\n".join(deduped)


def main() -> int:
    as_json = "--json" in sys.argv[1:]
    raw = sys.stdin.read()
    if not raw.strip():
        err = "ไม่ได้ output — เว็บอาจโหลดไม่ทันหรือถูกบล็อก"
        if as_json:
            print(json.dumps({"ok": False, "error": err}, ensure_ascii=False))
        else:
            print(f"[web-read] {err}", file=sys.stderr)
        return 1

    feed(raw)
    text = clean(build_lines())
    if not text:
        err = "แปลงเป็นข้อความไม่ได้ (หน้าว่าง?)"
        if as_json:
            print(json.dumps({"ok": False, "error": err}, ensure_ascii=False))
        else:
            print(f"[web-read] {err}", file=sys.stderr)
        return 1

    if as_json:
        print(json.dumps({
            "ok": True,
            "title": title,
            "text": text,
            "chars": len(text),
            "lines": len(text.splitlines()),
        }, ensure_ascii=False))
    else:
        if title:
            print(f"# {title}\n")
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

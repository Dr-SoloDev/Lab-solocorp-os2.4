#!/usr/bin/env python3
"""x_type.py — พิมพ์ข้อความลงช่อง compose ของ X ผ่าน CDP (Chrome ที่เปิดอยู่แล้ว)

ไม่กด Publish — ปุ่ม "โพสต์" เป็นของ Owner เสมอ
ใช้:  python scripts/x_type.py --port 9222 --text-file <file>
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--url-contains", default="x.com/compose")
    args = ap.parse_args()

    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    log(f"ข้อความ {len(text)} ตัวอักษร")

    import json as _json
    import urllib.request

    with urllib.request.urlopen(
            f"http://127.0.0.1:{args.port}/json/list", timeout=10) as r:
        targets = _json.loads(r.read().decode())

    page = None
    for t in targets:
        if t.get("type") == "page" and args.url_contains in (t.get("url") or ""):
            page = t
            break
    if not page:
        print("❌ ไม่พบ tab compose —", [t.get("url") for t in targets if t.get("type") == "page"][:5])
        return 1
    log(f"tab: {page['url'][:70]}")

    import websockets

    async with websockets.connect(page["webSocketDebuggerUrl"],
                                  max_size=None, origin=None) as ws:
            ctr = {"id": 0}

            async def cmd(method: str, params: dict | None = None) -> dict:
                ctr["id"] += 1
                mid = ctr["id"]
                await ws.send(json.dumps({"id": mid, "method": method,
                                         "params": params or {}}))
                while True:
                    raw = await ws.recv()
                    if isinstance(raw, (bytes, bytearray)):
                        raw = raw.decode("utf-8", "replace")
                    m = json.loads(raw)
                    if m.get("id") == mid:
                        return m

            # ── ตรวจว่า login แล้ว? ──
            r = await cmd("Runtime.evaluate", {
                "expression": "document.body.innerText.slice(0,3000)", "returnByValue": True})
            body = r.get("result", {}).get("result", {}).get("value") or ""
            logged_in = ("What's happening" in body) or ("tweetTextarea" in body) \
                or ("Post" in body and "Log in" not in body)
            log(f"login แล้ว: {logged_in}")
            if not logged_in:
                print("--- เนื้อหาหน้า ---")
                print(body[:400])
                return 1

            # ── focus ──
            r = await cmd("Runtime.evaluate", {
                "expression": (
                    "(()=>{const e=document.querySelector('div[data-testid=\"tweetTextarea_0\"]')"
                    "||document.querySelector('div[role=\"textbox\"][contenteditable=\"true\"]');"
                    "if(e){e.focus();return 'ok'}return 'none'})()"),
                "returnByValue": True})
            if r.get("result", {}).get("result", {}).get("value") != "ok":
                log("❌ ไม่พบช่อง compose")
                return 1
            log("focus ช่อง compose แล้ว")
            await asyncio.sleep(0.6)

            # ── พิมพ์ ──
            lines = text.split("\n")
            for i, line in enumerate(lines):
                await cmd("Input.insertText", {"text": line})
                if i < len(lines) - 1:
                    for ev in ("keyDown", "keyUp"):
                        await cmd("Input.dispatchKeyEvent", {
                            "type": ev, "key": "Enter", "code": "Enter",
                            "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13,
                            **({"text": "\r"} if ev == "keyDown" else {})})
                await asyncio.sleep(0.1)
            log(f"พิมพ์ {len(lines)} บรรทัดแล้ว")

            await asyncio.sleep(1.2)
            r = await cmd("Runtime.evaluate", {
                "expression": (
                    "(()=>{const e=document.querySelector('div[data-testid=\"tweetTextarea_0\"]')"
                    "||document.querySelector('div[role=\"textbox\"][contenteditable=\"true\"]');"
                    "return e?(e.innerText||e.textContent||''):''})()"),
                "returnByValue": True})
            got = (r.get("result", {}).get("result", {}).get("value") or "").strip()
            first = lines[0][:24]
            ok = first in got
            log(f"ตรวจช่อง: {len(got)} ตัวอักษร | บรรทัดแรกตรงไหม: {ok}")
            if not ok:
                print("--- ได้อะไรมา ---")
                print(got[:300])
                return 1
            print("\n--- เนื้อหาในช่อง ---")
            print(got[:500])
            print("--- จบ ---")
            print("\n✅ พร้อมแล้ว — กดปุ่ม 'โพสต์' ในหน้าต่างได้เลย")
            return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

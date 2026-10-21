#!/usr/bin/env python3
"""x_compose.py — เปิด X (โปรไฟล์ถาวร) + พิมพ์ข้อความลงช่อง compose ผ่าน CDP

ไม่กด Publish — ปุ่ม "โพสต์" เป็นของ Owner เสมอ
(เงื่อนไข X Video Kickstart Bonus §4(a): "not posted solely through unauthorized
automation" + ความเสี่ยงนโยบาย X ทั่วไป)

ทำไมใช้ CDP ตรง: ช่อง compose ของ X เป็น React contenteditable
→ ต้องได้ input event จริง (Input.insertText) ไม่ใช่แค่ set innerText
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SB = ROOT / "tools" / "stealth-browser-mcp"
sys.path.insert(0, str(SB / "src"))

DEFAULT_PROFILE = Path.home() / ".stealth-browser" / "profiles" / "x-solodev"
COMPOSE_URL = "https://x.com/compose/post"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def find_cdp_port(profile: Path) -> int | None:
    """หา --remote-debugging-port ของ Chrome ที่ใช้โปรไฟล์นี้"""
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().decode("utf-8", "replace")
        except Exception:
            continue
        if "remote-debugging-port" not in cmd or str(profile) not in cmd:
            continue
        for part in cmd.split("\x00"):
            if part.startswith("--remote-debugging-port="):
                return int(part.split("=", 1)[1])
    return None


async def cdp_eval(ws_send, ws_recv, method: str, params: dict | None = None) -> dict:
    """ส่งคำสั่ง CDP 1 ครั้ง + รอผลลัพธ์"""
    msg_id = cdp_eval.counter = getattr(cdp_eval, "counter", 0) + 1
    await ws_send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        raw = await ws_recv()
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", "replace")
        msg = json.loads(raw)
        if msg.get("id") == msg_id:
            return msg


async def type_via_cdp(port: int, text: str, url_contains: str = "x.com/compose") -> int:
    """พิมพ์ข้อความลงช่อง compose ผ่าน CDP → คืนจำนวนตัวอักษรที่เข้าไป"""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://127.0.0.1:{port}/json/list") as r:
            targets = await r.json()

    page = None
    for t in targets:
        if t.get("type") == "page" and url_contains in (t.get("url") or ""):
            page = t
            break
    if not page:
        pages = [t.get("url") for t in targets if t.get("type") == "page"]
        print(f"❌ ไม่พบ tab compose — pages: {pages}")
        return 0

    ws_url = page["webSocketDebuggerUrl"]
    print(f"→ tab: {page['url'][:70]}")

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(ws_url, max_msg_size=0) as ws:

            async def send(obj):
                await ws.send_str(json.dumps(obj))

            async def recv():
                return await ws.receive_str()

            # ── focus ช่อง compose ──
            sel = 'div[data-testid="tweetTextarea_0"]'
            res = await cdp_eval(send, recv, "Runtime.evaluate", {
                "expression": (
                    "(()=>{const e=document.querySelector('div[data-testid=\"tweetTextarea_0\"]')"
                    "||document.querySelector('div[role=\"textbox\"][contenteditable=\"true\"]');"
                    "if(e){e.focus();return 'ok'}return 'none'})()"
                ),
                "returnByValue": True,
            })
            found = res.get("result", {}).get("result", {}).get("value")
            print(f"focus ช่อง compose: {found}")
            if found != "ok":
                return 0
            await asyncio.sleep(0.6)

            # ── พิมพ์ทีละบรรทัด ──
            lines = text.split("\n")
            for i, line in enumerate(lines):
                await cdp_eval(send, recv, "Input.insertText", {"text": line})
                if i < len(lines) - 1:
                    for ev in ("keyDown", "keyUp"):
                        await cdp_eval(send, recv, "Input.dispatchKeyEvent", {
                            "type": ev, "key": "Enter", "code": "Enter",
                            "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13,
                            "text": "\r" if ev == "keyDown" else "",
                        })
                await asyncio.sleep(0.1)

            await asyncio.sleep(1.0)
            res = await cdp_eval(send, recv, "Runtime.evaluate", {
                "expression": (
                    "(()=>{const e=document.querySelector('div[data-testid=\"tweetTextarea_0\"]')"
                    "||document.querySelector('div[role=\"textbox\"][contenteditable=\"true\"]');"
                    "return e?(e.innerText||e.textContent||''):''})()"
                ),
                "returnByValue": True,
            })
            got = res.get("result", {}).get("result", {}).get("value") or ""
            got = got.strip()
            first = lines[0][:24]
            ok = first in got
            print(f"ตรวจช่อง: {len(got)} ตัวอักษร | บรรทัดแรกตรงไหม: {ok}")
            if not ok:
                print("--- ได้อะไรมา ---")
                print(got[:300])
            return len(got) if ok else 0


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--profile", default=str(DEFAULT_PROFILE))
    ap.add_argument("--url", default=COMPOSE_URL)
    ap.add_argument("--keep-open", action="store_true", default=True)
    args = ap.parse_args()

    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    log(f"ข้อความ {len(text)} ตัวอักษร")

    os.environ.setdefault("DISPLAY", ":0")
    import server  # noqa: E402

    def _tool(name):
        t = getattr(server, name)
        return getattr(t, "fn", t)

    _spawn, _navigate = _tool("spawn_browser"), _tool("navigate")

    profile = Path(args.profile)
    profile.mkdir(parents=True, exist_ok=True)

    log("เปิด Chrome (headful, โปรไฟล์ถาวร)…")
    inst = await _spawn(
        headless=False,
        user_data_dir=str(profile),
        viewport_width=1280,
        viewport_height=1000,
        idle_timeout_seconds=None,
    )
    iid = inst.get("instance_id") or inst.get("id")
    log(f"instance_id = {iid}")

    port = None
    for _ in range(20):
        port = find_cdp_port(profile)
        if port:
            break
        await asyncio.sleep(1)
    if not port:
        log("❌ หา CDP port ไม่ได้")
        return 1
    log(f"CDP port = {port}")

    log(f"ไปที่ {args.url}")
    await _navigate(iid, args.url, timeout=45000)
    await asyncio.sleep(4)

    n = await type_via_cdp(port, text)
    if n <= 0:
        log("❌ พิมพ์ไม่สำเร็จ")
        return 1

    log("")
    log("=" * 64)
    log(f"  ✅ พิมพ์เรียบร้อย {n} ตัวอักษร — พร้อมกด Publish")
    log("  👉 ดูหน้าต่าง Chrome → กดปุ่ม 'โพสต์' เอง")
    log("  ⚠️  ห้ามปิดหน้าต่างก่อนกด")
    log("=" * 64)

    try:
        while True:
            await asyncio.sleep(30)
    except KeyboardInterrupt:
        log("จบ")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

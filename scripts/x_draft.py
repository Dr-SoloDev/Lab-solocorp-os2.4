#!/usr/bin/env python3
"""x_draft.py — เตรียมโพสต์บน X เป็น draft ให้ Owner กด Publish เอง

ทำไมต้องมีขั้นตอนนี้: Terms ของ X Video Kickstart Bonus §4(a) ห้าม
"posted solely through unauthorized automation" และกฎ X ทั่วไปก็เสี่ยง
→ เรา**พิสูจน์ได้แค่ถึงขั้น "พร้อมกดโพสต์"** การกด Publish = คนทำเสมอ

ขั้นตอน:
  1. เปิด Chrome แบบมีจอ (headful) บน DISPLAY ของเครื่อง + โปรไฟล์ถาวร
  2. ไปที่ x.com/compose/post
  3. รอจนกว่าคุณ login เสร็จ (ตรวจจากเนื้อหาหน้า)
  4. พิมพ์ข้อความลงช่อง compose
  5. ตรวจว่าข้อความเข้าไปแล้ว → เปิดหน้าค้างไว้ให้คุณกด Publish

ใช้:
  python scripts/x_draft.py --text-file bus/media/creator/<slug>/<วัน>/post-01.md
  python scripts/x_draft.py --text-file ... --wait 600      # รอ login นานขึ้น
  python scripts/x_draft.py --text "..." --headless         # ทดสอบไม่ต้อง login
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SB = ROOT / "tools" / "stealth-browser-mcp"
sys.path.insert(0, str(SB / "src"))

DEFAULT_PROFILE = Path.home() / ".stealth-browser" / "profiles" / "x-solodev"
COMPOSE_URL = "https://x.com/compose/post"

# ตัวบอกว่า "login แล้ว" (ตรวจจากเนื้อหาหน้า)
LOGGED_IN_MARKERS = (
    "tweetTextarea", "tweetButton", "Profile", "โพสต์", "Notifications",
    "การแจ้งเตือน", "Home", "หน้าแรก",
)
LOGGED_OUT_MARKERS = ("Log in", "เข้าสู่ระบบ", "Sign up", "สมัครใช้", "Create account")

# ช่องพิมพ์ของ X (เรียงตามความเจาะจร)
COMPOSE_SELECTORS = (
    'div[data-testid="tweetTextarea_0"]',
    'div[role="textbox"][contenteditable="true"]',
    'div[data-testid="tweetTextarea_0"] textarea',
    'textarea[data-testid="tweetTextarea_0"]',
)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def main() -> int:
    ap = argparse.ArgumentParser(description="เตรียมโพสต์ X เป็น draft")
    ap.add_argument("--text", help="ข้อความโพสต์")
    ap.add_argument("--text-file", help="ไฟล์ที่มีข้อความโพสต์")
    ap.add_argument("--profile", default=str(DEFAULT_PROFILE),
                    help="โปรไฟล์ Chrome (เก็บ cookie ข้าม session)")
    ap.add_argument("--wait", type=int, default=600,
                    help="วินาทีที่รอ login")
    ap.add_argument("--headless", action="store_true", help="ไม่มีจอ (ทดสอบเท่านั้น)")
    ap.add_argument("--url", default=COMPOSE_URL)
    args = ap.parse_args()

    text = args.text
    if not text and args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        print("❌ ไม่มีข้อความ (ใช้ --text หรือ --text-file)")
        return 2

    os.environ.setdefault("DISPLAY", ":0")
    import server  # noqa: E402  (ต้องอยู่ใน src/)

    def _tool(name):
        """FastMCP ครอบ tool เป็น FunctionTool → ดึงฟังก์ชันข้างในออกมาเรียก"""
        t = getattr(server, name)
        return getattr(t, "fn", t)

    _spawn, _navigate, _click = _tool("spawn_browser"), _tool("navigate"), _tool("click_element")
    _type_text, _get_content = _tool("type_text"), _tool("get_page_content")

    profile = Path(args.profile)
    profile.mkdir(parents=True, exist_ok=True)
    log(f"โปรไฟล์: {profile}")
    log(f"ข้อความ {len(text)} ตัวอักษร")

    log("กำลังเปิด Chrome…")
    inst = await _spawn(
        headless=args.headless,
        user_data_dir=str(profile),
        viewport_width=1280,
        viewport_height=1000,
        idle_timeout_seconds=None,
    )
    iid = inst.get("instance_id") or inst.get("id")
    if not iid:
        log(f"❌ เปิดไม่ได้: {inst}")
        return 1
    log(f"instance_id = {iid}")

    try:
        log(f"ไปที่ {args.url}")
        await _navigate(iid, args.url, timeout=45000)
        await asyncio.sleep(3)

        # ── รอ login ──
        deadline = time.time() + args.wait
        logged_in = False
        while time.time() < deadline:
            try:
                content = await _get_content(iid)
                body = str(content.get("content", content) if isinstance(content, dict) else content)
            except Exception:
                body = ""
            if any(m in body for m in LOGGED_IN_MARKERS) and not any(
                    m in body for m in LOGGED_OUT_MARKERS):
                logged_in = True
                break
            if args.headless:
                break
            time.sleep(3)

        if not logged_in:
            log("⚠️ ตรวจไม่พบว่า login แล้ว — จะลองพิมพ์ต่อ (ถ้ายังไม่ login จะไม่สำเร็จ)")
        else:
            log("✅ login แล้ว")

        # ── พิมพ์ข้อความ ──
        ok = False
        for sel in COMPOSE_SELECTORS:
            try:
                clicked = await _click(iid, sel, timeout=6000)
            except Exception:
                clicked = False
            if not clicked:
                continue
            time.sleep(1)
            try:
                typed = await _type_text(iid, sel, text, clear_first=True)
            except Exception as e:
                log(f"   พิมพ์ไม่สำเร็จที่ {sel}: {e}")
                continue
            if typed:
                log(f"✅ พิมพ์ผ่าน selector: {sel}")
                ok = True
                break

        if not ok:
            log("❌ พิมพ์ไม่สำเร็จ — เบราว์เซอร์ยังเปิดไว้ ให้ตรวจเอง")
            return 1

        await asyncio.sleep(1)
        # ── ยืนยันว่าข้อความอยู่ในช่อง ──
        try:
            content = await _get_content(iid)
            body = str(content.get("content", content) if isinstance(content, dict) else content)
            head = text.splitlines()[0][:28]
            log(f"ตรวจช่อง compose: {'พบข้อความ ✅' if head in body else 'ยังไม่เห็นข้อความ ⚠️'}")
        except Exception as e:
            log(f"ตรวจช่อง compose ไม่ได้: {e}")

        log("")
        log("=" * 62)
        log("  ✅ พร้อมแล้ว — เบราว์เซอร์เปิดค้างไว้")
        log("  👉 ตรวจในหน้าต่าง Chrome → กดปุ่ม 'โพสต์' เพื่อเผยแพร่")
        log("  ⚠️  ห้ามปิดเบราว์เซอร์ก่อนกดโพสต์")
        log("=" * 62)
        log(f"instance_id = {iid}")

        # ค้างไว้ให้ Owner กด Publish
        try:
            while True:
                time.sleep(30)
        except KeyboardInterrupt:
            log("ปิดเบราว์เซอร์…")
        return 0
    finally:
        # ไม่ close_instance — ต้องเก็บหน้าค้างไว้ให้ Owner กด Publish
        pass


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

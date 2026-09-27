"""สะพาน SoloCorp → flowkit (Google Flow).

Phase 2 bridge — ใช้งานจริงวันเริ่ม Pro (Day-1 checklist ใน bus/plans/flow-pro-3month.md).
ก่อนหน้านั้น is_ready() = False และ loop จะ SKIP (ไม่พัง, ไม่เผาอะไร).

Endpoints อ้างจาก flowkit README + config.py (verify Day-1):
  GET  http://127.0.0.1:8100/health
  POST http://127.0.0.1:8100/api/flow/generate-video-omni-text  (4/6/8/10s)
"""
from __future__ import annotations

import json
import os
import urllib.request

FLOWKIT_URL = os.environ.get("FLOWKIT_URL", "http://127.0.0.1:8100")
TIMEOUT = 15


def is_ready() -> tuple[bool, str]:
    """flowkit agent ตอบไหม + extension ต่ออยู่ไหม"""
    try:
        req = urllib.request.Request(f"{FLOWKIT_URL}/health", method="GET")
        resp = json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read())
        if resp.get("extension_connected") is False:
            return False, "extension ไม่ต่อ (เปิดแท็บ flow.google.com ค้างไว้)"
        return True, "ready"
    except Exception as e:
        return False, f"flowkit ไม่ตอบ: {e}"


def generate_segment(prompt_en: str, seconds: int = 10,
                     aspect: str = "16:9") -> dict:
    """ยิงเจน 1 ท่อน (Omni) — คืน dict {ok, request_id|error}"""
    body = json.dumps({
        "prompt": prompt_en,
        "duration": seconds,
        "aspect_ratio": aspect,
        "model_family": "omni_flash",  # ถูกสุดที่ 10s ได้ (15 credits/720p)
    }).encode()
    try:
        req = urllib.request.Request(
            f"{FLOWKIT_URL}/api/flow/generate-video-omni-text",
            data=body, headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read())
        rid = resp.get("request_id") or resp.get("id") or "?"
        return {"ok": True, "request_id": str(rid), "raw": resp}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}

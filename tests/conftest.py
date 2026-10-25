"""pytest — isolation สำหรับ runtime state ที่ LLM provider เขียน

ทำไมต้องมี
────────────
`workers/llm_provider.think()` เขียน 2 ไฟล์ตอนรันจริง:
  · `bus/system/token-ledger.jsonl` — usage ต่อ call
  · `bus/system/llm_quota.json`      — quota lock (429/402)

ถ้าเทสต์ไม่แยกออก:
  1. เทสต์จะเขียนของจริง (incident 2026-10-25: 35 บรรทัดขยะจากเทสต์หลุดเข้า ledger)
  2. quota lock ที่ค้างอยู่จะทำให้เทสต์อื่น **ล้มแบบไม่เกี่ยวกับโค้ด** (think คืนทันที)
     → เทสต์ไม่ deterministic และหาสาเหตุยาก

fixture นี้ autouse → ทุกเทสต์ได้ tmp path ของตัวเอง ไม่ต้องจำไปใส่ทีละไฟล์
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_llm_runtime_state(tmp_path, monkeypatch):
    """ชี้ ledger / quota / opencode.db ไปที่ tmp ของเทสต์นั้น"""
    from workers import token_ledger

    monkeypatch.setattr(
        token_ledger, "LEDGER_PATH", tmp_path / "token-ledger.jsonl", raising=False
    )
    monkeypatch.setattr(
        token_ledger, "QUOTA_PATH", tmp_path / "llm_quota.json", raising=False
    )
    monkeypatch.setattr(
        token_ledger, "DB_PATH", tmp_path / "opencode.db", raising=False
    )

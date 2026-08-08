"""Fallback verification — daily_brief/subscription_audit EN fallback (CMD-001-F).

Deterministic: mock think() → empty/error → assert fallback path invoked.
(ไม่พึ่งพา free-tier LLM ที่ไม่เสถียร — ตรวจกลไก ไม่ใช่ provider)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestDailyBriefFallback:
    def test_empty_response_triggers_fallback(self, monkeypatch):
        from loop_runner.loops import daily_brief

        calls = []

        async def fake_think(prompt, system_prompt="", **kw):
            calls.append(prompt)
            return "⚠️ LLM ไม่พร้อม: empty response"

        async def fake_think_ok(prompt, system_prompt="", **kw):
            return "FALLBACK EN RESULT"

        monkeypatch.setattr(daily_brief, "think", fake_think)
        monkeypatch.setattr(daily_brief, "_fetch_facts", lambda: [])
        loop = daily_brief.DailyBriefLoop()
        # primary คืน ⚠️ → ต้องเรียก fallback (fake_think_ok ตอบสำเร็จ)
        monkeypatch.setattr(loop, "_fallback_en", staticmethod(lambda facts: "FALLBACK EN RESULT"))
        result = loop.run()
        assert "FALLBACK EN RESULT" in result
        assert len(calls) == 1  # fallback ใช้ prompt ของตัวเอง ไม่ใช่ primary ซ้ำ

    def test_llm_error_does_not_raise(self, monkeypatch):
        from loop_runner.loops import daily_brief

        async def boom(prompt, system_prompt="", **kw):
            raise RuntimeError("connection refused")

        monkeypatch.setattr(daily_brief, "think", boom)
        monkeypatch.setattr(daily_brief, "_fetch_facts", lambda: [])
        result = daily_brief.DailyBriefLoop().run()
        assert result.startswith("⚠️")  # ไม่ raise


class TestSubscriptionAuditFallback:
    def test_empty_response_triggers_fallback(self, monkeypatch):
        from loop_runner.loops import subscription_audit

        async def fake_think(prompt, system_prompt="", **kw):
            return "⚠️ LLM ไม่พร้อม: empty response"

        monkeypatch.setattr(subscription_audit, "think", fake_think)
        monkeypatch.setattr(subscription_audit, "_fetch_context", lambda: {"facts": [], "queue": []})
        loop = subscription_audit.SubscriptionAuditLoop()
        monkeypatch.setattr(loop, "_fallback_en", staticmethod(lambda facts: "FALLBACK EN RESULT"))
        result = loop.run()
        assert "FALLBACK EN RESULT" in result
        assert result.startswith("## CFO Subscription Audit")

    def test_error_does_not_raise(self, monkeypatch):
        from loop_runner.loops import subscription_audit

        async def boom(prompt, system_prompt="", **kw):
            raise RuntimeError("connection refused")

        monkeypatch.setattr(subscription_audit, "think", boom)
        monkeypatch.setattr(subscription_audit, "_fetch_context", lambda: {"facts": [], "queue": []})
        result = subscription_audit.SubscriptionAuditLoop().run()
        assert result.startswith("⚠️")  # ไม่ raise

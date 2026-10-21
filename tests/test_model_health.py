"""Tests for model health check (กัน LLM chain ตายเงียบ)

เจอเคสจริง 2026-10-20: MODEL_FALLBACKS มีชื่อโมเดลที่ไม่มีอยู่จริง
→ ทุกโมเดลคืน "empty response" → agent 19 ตัว "ตาบอด" โดยไม่มี error ชัดเจน
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workers import llm_provider as lp  # noqa: E402


# ══════════════════════════════════════════════════════════════════════
# Chain ปัจจุบัน
# ══════════════════════════════════════════════════════════════════════


class TestModelChain:
    """chain ต้องไม่มีชื่อซ้ำ และไม่มีโมเดลที่รู้ว่าตายอยู่ใน chain"""

    def test_no_duplicates(self):
        assert len(lp.MODEL_FALLBACKS) == len(set(lp.MODEL_FALLBACKS))

    def test_default_model_is_first_in_chain(self):
        assert lp.MODEL_FALLBACKS[0] == lp.DEFAULT_MODEL

    def test_dead_models_not_in_chain(self):
        """โมเดลที่ยืนยันว่าใช้ไม่ได้ ต้องไม่อยู่ใน chain"""
        dead_in_chain = [m for m in lp.MODEL_FALLBACKS if m in lp.DEAD_MODELS]
        assert dead_in_chain == [], f"โมเดลที่ตายอยู่ใน chain: {dead_in_chain}"

    def test_chain_not_empty(self):
        assert len(lp.MODEL_FALLBACKS) >= 2

    def test_known_gone_models_are_marked_dead(self):
        """ชื่อโมเดลที่หายไปต้องอยู่ใน DEAD_MODELS (ไม่งั้นจะเป็นตัวหลักได้)"""
        for gone in ("opencode/muse-spark-1.3-contributor-free",
                     "opencode/space-bunny-free"):
            assert gone in lp.DEAD_MODELS


# ══════════════════════════════════════════════════════════════════════
# audit_models
# ══════════════════════════════════════════════════════════════════════


class TestAuditModels:
    """audit_models — เทียบ chain กับโมเดลที่มีจริง"""

    def test_reports_all_fields(self, monkeypatch):
        monkeypatch.setattr(
            lp, "list_available_models",
            lambda prefix="opencode/": ["opencode/a-free", "opencode/b-free"],
        )
        r = lp.audit_models(use_cache=False)
        for field in ("ok", "chain", "available", "missing", "usable",
                      "candidates", "checked_at", "stale", "error"):
            assert field in r, f"ไม่มี field '{field}'"

    def test_detects_missing(self, monkeypatch):
        monkeypatch.setattr(
            lp, "list_available_models",
            lambda prefix="opencode/": ["opencode/keep-free"],
        )
        monkeypatch.setattr(lp, "MODEL_FALLBACKS",
                            ["opencode/keep-free", "opencode/GONE-free"])
        r = lp.audit_models(use_cache=False)
        assert r["ok"] is False
        assert r["missing"] == ["opencode/GONE-free"]
        assert r["usable"] == ["opencode/keep-free"]

    def test_all_present_is_ok(self, monkeypatch):
        monkeypatch.setattr(
            lp, "list_available_models",
            lambda prefix="opencode/": ["opencode/a-free", "opencode/b-free"],
        )
        monkeypatch.setattr(lp, "MODEL_FALLBACKS",
                            ["opencode/a-free", "opencode/b-free"])
        r = lp.audit_models(use_cache=False)
        assert r["ok"] is True
        assert r["missing"] == []

    def test_candidates_are_models_outside_chain(self, monkeypatch):
        monkeypatch.setattr(
            lp, "list_available_models",
            lambda prefix="opencode/": ["opencode/in-chain", "opencode/new-one"],
        )
        monkeypatch.setattr(lp, "MODEL_FALLBACKS", ["opencode/in-chain"])
        r = lp.audit_models(use_cache=False)
        assert r["candidates"] == ["opencode/new-one"]

    def test_handles_unavailable_listing(self, monkeypatch):
        """เรียก opencode ไม่ได้ → ข้ามการตรวจ ไม่ต้อง error"""
        monkeypatch.setattr(lp, "list_available_models", lambda prefix="opencode/": [])
        r = lp.audit_models(use_cache=False)
        assert r["ok"] is True
        assert r["error"]
        assert r["missing"] == []

    def test_uses_cache_when_available(self, monkeypatch, tmp_path):
        cache = tmp_path / "mh.json"
        monkeypatch.setattr(lp, "_MODEL_CACHE_PATH", cache)
        calls = []

        def fake_list(prefix="opencode/"):
            calls.append(1)
            return ["opencode/x-free"]

        monkeypatch.setattr(lp, "list_available_models", fake_list)
        monkeypatch.setattr(lp, "MODEL_FALLBACKS", ["opencode/x-free"])

        lp.audit_models(use_cache=True)          # ครั้งแรก → สร้าง cache
        assert cache.exists()
        assert len(calls) == 1

        lp.audit_models(use_cache=True)          # ครั้งที่ 2 → ใช้ cache
        assert len(calls) == 1, "ควรใช้ cache ไม่เรียก opencode ซ้ำ"

    def test_stale_cache_triggers_refresh(self, monkeypatch, tmp_path):
        import json
        from datetime import datetime, timedelta, timezone

        cache = tmp_path / "mh.json"
        old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        cache.write_text(json.dumps({
            "checked_at": old, "available": ["opencode/old-free"],
        }), encoding="utf-8")
        monkeypatch.setattr(lp, "_MODEL_CACHE_PATH", cache)

        calls = []
        monkeypatch.setattr(
            lp, "list_available_models",
            lambda prefix="opencode/": (calls.append(1), ["opencode/new-free"])[1],
        )
        monkeypatch.setattr(lp, "MODEL_FALLBACKS", ["opencode/new-free"])

        r = lp.audit_models(use_cache=True)
        assert len(calls) == 1, "cache เก่าต้อง refresh"
        assert r["usable"] == ["opencode/new-free"]


# ══════════════════════════════════════════════════════════════════════
# Watchdog integration
# ══════════════════════════════════════════════════════════════════════


class TestWatchdogModelHealth:
    """watchdog ต้องเรียก model health check"""

    def test_function_exists(self):
        from central_bus.monitor_watchdog import check_model_health
        assert callable(check_model_health)

    def test_returns_report(self, monkeypatch):
        from central_bus import monitor_watchdog as mw
        monkeypatch.setattr(
            mw, "check_model_health",
            lambda use_cache=True: {"ok": True, "chain": [], "missing": []},
        )
        assert mw.check_model_health()["ok"] is True

    def test_survives_import_error(self, monkeypatch):
        """ถ้า import llm_provider ไม่ได้ → ข้าม ไม่ error"""
        from central_bus import monitor_watchdog as mw
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *a, **k):
            if name == "workers.llm_provider":
                raise ImportError("simulated")
            return real_import(name, *a, **k)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        r = mw.check_model_health()
        assert r["ok"] is True
        assert r.get("skipped") is True

    def test_watchdog_script_calls_it(self):
        src = Path(__file__).resolve().parent.parent / "scripts" / "_watchdog_run.py"
        text = src.read_text(encoding="utf-8")
        assert "check_model_health" in text
        assert "_report_to_ceo" in text


class TestModelHealthScript:
    """scripts/check-model-health.py ต้องมีและใช้งานได้"""

    def test_script_exists(self):
        p = Path(__file__).resolve().parent.parent / "scripts" / "check-model-health.py"
        assert p.exists()

    def test_script_has_modes(self):
        p = Path(__file__).resolve().parent.parent / "scripts" / "check-model-health.py"
        text = p.read_text(encoding="utf-8")
        for mode in ("--verify", "--verify-all", "--candidates"):
            assert mode in text

    def test_probe_detects_dead_markers(self):
        import importlib.util
        p = Path(__file__).resolve().parent.parent / "scripts" / "check-model-health.py"
        spec = importlib.util.spec_from_file_location("_cmh", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # DEAD_MARKERS ต้องครอบคลุมเคส agents_md ที่เจอจริง
        assert any("agents_md" in m for m in mod.DEAD_MARKERS)
        assert any("model not found" in m for m in mod.DEAD_MARKERS)

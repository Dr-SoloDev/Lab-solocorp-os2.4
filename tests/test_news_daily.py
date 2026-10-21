"""Tests for W3 — news_daily loop + news fetcher + facts write endpoint

Covers:
  * solocorp_skills/news.py  — watchlist parsing, RSS parsing, dedupe, digest
  * loop_runner/loops/news_daily.py — loop registration + guards
  * central_bus/main.py     — POST /v1/facts (write channel for the facts store)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solocorp_skills.news import (  # noqa: E402
    NewsItem,
    NewsSource,
    build_digest,
    dedupe,
    group_by_dept,
    load_watchlist,
    _clean,
    _safe_url,
)

RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>ข่าวทดสอบ</title>
  <item>
    <title>ธุรกิจไทยโตแรงไตรมาสนี้</title>
    <link>https://example.com/a</link>
    <description>ยอดขายโต 20% &amp; ดีขึ้น</description>
    <pubDate>Mon, 20 Oct 2026 08:00:00 +0700</pubDate>
  </item>
  <item>
    <title>SME ไทยต้องการเงินหมุน</title>
    <link>https://example.com/b</link>
    <description>วิกฤติเงินหมุนปลายปี</description>
  </item>
</channel></rss>"""

ATOM_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>AI เปลี่ยนเกม</title>
    <link rel="alternate" href="https://example.com/atom-1"/>
    <summary>เรื่องสรุป</summary>
    <updated>2026-10-20T08:00:00Z</updated>
  </entry>
</feed>"""


# ══════════════════════════════════════════════════════════════════════
# Watchlist
# ══════════════════════════════════════════════════════════════════════


class TestWatchlist:
    """load_watchlist — อ่าน markdown table"""

    def _write(self, tmp_path, body):
        p = tmp_path / "watchlist.md"
        p.write_text(body, encoding="utf-8")
        return p

    def test_parses_active_rows(self, tmp_path):
        p = self._write(tmp_path, """
| # | แผนก | ชื่อ | URL | โหมด | สถานะ |
|:--|:--|:--|:--|:--|:--|
| 1 | cmo | ข่าวธุรกิจ | https://example.com/rss | rss | ✅ active |
| 2 | sales | ข่าวเทค | https://example.com/feed | rss | ✅ active |
""")
        srcs = load_watchlist(p)
        assert len(srcs) == 2
        assert srcs[0].dept == "cmo"
        assert srcs[0].name == "ข่าวธุรกิจ"
        assert srcs[0].mode == "rss"

    def test_skips_pending_rows(self, tmp_path):
        p = self._write(tmp_path, """
| 1 | cmo | ข่าว | https://example.com/rss | rss | ⏳ pending |
| 2 | cmo | ข่าว2 | https://example.com/rss2 | rss | ✅ active |
""")
        srcs = load_watchlist(p)
        assert len(srcs) == 1
        assert srcs[0].name == "ข่าว2"

    def test_skips_header_and_separator(self, tmp_path):
        p = self._write(tmp_path, """
| # | แผนก | ชื่อ | URL | โหมด | สถานะ |
|:--|:--|:--|:--|:--|:--|
| 1 | cmo | ข่าว | https://example.com/rss | rss | ✅ active |
""")
        assert len(load_watchlist(p)) == 1

    def test_skips_non_http(self, tmp_path):
        p = self._write(tmp_path, """
| 1 | cmo | เสีย | not-a-url | rss | ✅ active |
""")
        assert load_watchlist(p) == []

    def test_web_mode_detected(self, tmp_path):
        p = self._write(tmp_path, """
| 1 | cmo | เว็บ | https://example.com | web | ✅ active |
""")
        assert load_watchlist(p)[0].mode == "web"

    def test_missing_file_returns_empty(self, tmp_path):
        assert load_watchlist(tmp_path / "ไม่มี.md") == []

    def test_real_watchlist_is_valid(self):
        """watchlist จริงใน repo ต้อง parse ได้และมีแหล่งข่าว"""
        srcs = load_watchlist()
        assert len(srcs) > 0, "watchlist จริงต้องมีแหล่งข่าวอย่างน้อย 1"
        for s in srcs:
            assert s.url.startswith("http")
            assert s.dept and s.name


# ══════════════════════════════════════════════════════════════════════
# RSS parsing
# ══════════════════════════════════════════════════════════════════════


class TestRssParsing:
    """fetch_rss — parse RSS 2.0 / Atom (ใช้ monkeypatch ไม่ต่อเน็ต)"""

    def _patch(self, monkeypatch, payload: bytes):
        import io
        import urllib.request

        class FakeResp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        monkeypatch.setattr(
            urllib.request, "urlopen",
            lambda *a, **k: FakeResp(payload),
        )

    def test_parses_rss_items(self, monkeypatch):
        from solocorp_skills.news import fetch_rss
        self._patch(monkeypatch, RSS_SAMPLE.encode("utf-8"))
        items = fetch_rss("https://example.com/rss")
        assert len(items) == 2
        assert items[0].title == "ธุรกิจไทยโตแรงไตรมาสนี้"
        assert items[0].url == "https://example.com/a"

    def test_cleans_html_entities(self, monkeypatch):
        from solocorp_skills.news import fetch_rss
        self._patch(monkeypatch, RSS_SAMPLE.encode("utf-8"))
        items = fetch_rss("https://example.com/rss")
        assert "&amp;" not in items[0].summary
        assert "20%" in items[0].summary

    def test_parses_atom(self, monkeypatch):
        from solocorp_skills.news import fetch_rss
        self._patch(monkeypatch, ATOM_SAMPLE.encode("utf-8"))
        items = fetch_rss("https://example.com/atom")
        assert len(items) == 1
        assert items[0].title == "AI เปลี่ยนเกม"
        assert items[0].url == "https://example.com/atom-1"

    def test_respects_limit(self, monkeypatch):
        from solocorp_skills.news import fetch_rss
        self._patch(monkeypatch, RSS_SAMPLE.encode("utf-8"))
        assert len(fetch_rss("https://example.com/rss", limit=1)) == 1

    def test_clean_strips_tags(self):
        assert _clean("<b>ต้อน</b> สวัสดี") == "ต้อน สวัสดี"

    def test_clean_truncates(self):
        assert len(_clean("x" * 1000, limit=50)) == 50


class TestSafeUrl:
    """_safe_url — encode อักขระไทยใน URL"""

    def test_encodes_thai(self):
        out = _safe_url("https://news.google.com/rss/search?q=ธุรกิจไทย")
        assert "ธุรกิจ" not in out
        assert "%E0%B8%98" in out

    def test_keeps_url_structure(self):
        out = _safe_url("https://news.google.com/rss/search?q=a+b&hl=th")
        assert out.startswith("https://news.google.com/rss/search?q=a+b&hl=th")

    def test_ascii_url_unchanged(self):
        url = "https://techcrunch.com/feed/"
        assert _safe_url(url) == url


# ══════════════════════════════════════════════════════════════════════
# Dedupe + digest
# ══════════════════════════════════════════════════════════════════════


class TestDedupe:
    """dedupe — ไม่ส่งข่าวเดิมซ้ำ"""

    def test_filters_seen(self):
        items = [
            NewsItem(title="ข่าว ก", url="https://a.com/1"),
            NewsItem(title="ข่าว ข", url="https://a.com/2"),
        ]
        seen = [items[0].key()]
        fresh, new_seen = dedupe(items, seen)
        assert len(fresh) == 1
        assert fresh[0].title == "ข่าว ข"
        assert len(new_seen) == 2

    def test_filters_duplicates_in_batch(self):
        items = [
            NewsItem(title="ข่าวเดียวกัน", url="https://a.com/1"),
            NewsItem(title="ข่าวเดียวกัน", url="https://a.com/1"),
        ]
        fresh, _ = dedupe(items, [])
        assert len(fresh) == 1

    def test_ignores_query_string_for_key(self):
        a = NewsItem(title="ข่าว", url="https://a.com/1?utm=x")
        b = NewsItem(title="ข่าว", url="https://a.com/1?utm=y")
        fresh, _ = dedupe([a, b], [])
        assert len(fresh) == 1

    def test_empty_input(self):
        fresh, seen = dedupe([], [])
        assert fresh == [] and seen == []


class TestDigest:
    """build_digest + group_by_dept"""

    def test_digest_has_headlines_and_urls(self):
        items = [NewsItem(title="หัวข้อข่าว", url="https://a.com/1",
                          summary="สรุป", source="แหล่ง", dept="cmo")]
        d = build_digest(items, "cmo")
        assert "หัวข้อข่าว" in d
        assert "https://a.com/1" in d
        assert "แหล่ง" in d
        assert "cmo" in d

    def test_group_by_dept(self):
        items = [
            NewsItem(title="a", url="u1", dept="cmo"),
            NewsItem(title="b", url="u2", dept="sales"),
            NewsItem(title="c", url="u3", dept="cmo"),
        ]
        groups = group_by_dept(items)
        assert len(groups["cmo"]) == 2
        assert len(groups["sales"]) == 1


# ══════════════════════════════════════════════════════════════════════
# Loop + Bus integration
# ══════════════════════════════════════════════════════════════════════


class TestNewsDailyLoop:
    """loop_runner — news_daily ต้องลงทะเบียนและมี guard"""

    def test_loop_registered(self):
        from loop_runner.loops import ALL_LOOPS
        ids = [l.loop_id for l in ALL_LOOPS]
        assert "news_daily" in ids

    def test_loop_guards(self):
        from loop_runner.loops.news_daily import (
            NewsDailyLoop, MAX_SOURCES_PER_RUN, DEPT_INBOX,
        )
        loop = NewsDailyLoop()
        assert loop.trust_level == 1
        assert loop.model_hint is None
        assert MAX_SOURCES_PER_RUN > 0
        # ทุกแผนกที่ประกาศต้องมี inbox profile ที่ถูกต้อง
        for dept, target in DEPT_INBOX.items():
            assert isinstance(target, str) and target

    def test_dept_inbox_targets_are_real_profiles(self):
        """ชื่อ inbox ต้องอยู่ในรายการ profile ของ scripts/inbox.py"""
        import importlib.util
        src = Path(__file__).resolve().parent.parent / "scripts" / "inbox.py"
        spec = importlib.util.spec_from_file_location("_inbox_mod", src)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        known = set(mod.VALID)
        assert known, "ไม่พบรายการ profile ใน inbox.py"
        from loop_runner.loops.news_daily import DEPT_INBOX
        for dept, target in DEPT_INBOX.items():
            assert target in known, f"{dept} → '{target}' ไม่ใช่ inbox profile ที่มีอยู่"

    def test_should_run_is_date_gated(self):
        """should_run ต้องเป็น false ถ้าวันนี้รันแล้ว"""
        from loop_runner.loops.news_daily import NewsDailyLoop
        from loop_runner.state import last_run
        assert callable(NewsDailyLoop().should_run)


class TestFactsEndpoint:
    """facts store ต้องมีทางเขียน (ไม่งั้น W3 จะส่งข่าวไม่ได้)"""

    def test_routes_exist(self):
        from central_bus.main import app
        paths = {getattr(r, "path", "") for r in app.routes}
        assert "/v1/facts" in paths

    def test_post_fact_requires_key_field(self):
        """ไม่ส่ง key → 400 (ผ่าน auth แล้ว)"""
        from fastapi.testclient import TestClient
        from central_bus.main import app
        client = TestClient(app)
        client.headers.setdefault("X-API-Key", "sk-solocorp-admin-local-dev-001")
        r = client.post("/v1/facts", json={"value": "x"})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_post_fact_requires_auth(self):
        """ไม่มี API key → 401 จาก auth middleware"""
        from fastapi.testclient import TestClient
        from central_bus.main import app
        client = TestClient(app)
        r = client.post("/v1/facts", json={"key": "x", "value": 1})
        assert r.status_code == 401

    def test_post_and_read_fact(self):
        from fastapi.testclient import TestClient
        from central_bus.main import app
        client = TestClient(app)
        client.headers.setdefault("X-API-Key", "sk-solocorp-admin-local-dev-001")
        key = "test.news.unit"
        r = client.post("/v1/facts", json={
            "key": key,
            "value": {"count": 1},
            "metadata": {"workstream": "OWN-BIZ", "sensitivity": "PUB"},
            "updated_by": "unit-test",
        })
        assert r.status_code == 200
        assert r.json()["version"] >= 1
        # เขียนซ้ำ → version เพิ่ม
        r2 = client.post("/v1/facts", json={
            "key": key,
            "value": {"count": 2},
            "metadata": {"workstream": "OWN-BIZ", "sensitivity": "PUB"},
        })
        assert r2.json()["version"] > r.json()["version"]

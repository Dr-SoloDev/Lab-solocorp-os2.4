"""Tests for the web capability (web_read / web_search).

Covers the three integration points built in W1+W2:
  * solocorp_skills.web  — shared client (URL guard, untrusted wrapping, SERP parsing)
  * workers/agents/base_agent.py  — BaseAgent.web_read() / .web_search()
  * solocorp_mcp/server.py         — solocorp_web_read / solocorp_web_search tools
  * central_bus/main.py            — POST /v1/web-read endpoint

Live network tests are skipped when docker is unavailable so CI stays offline-safe.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solocorp_skills.web import (  # noqa: E402
    UNTRUSTED_CLOSE,
    UNTRUSTED_OPEN,
    WebError,
    _parse_serp,
    read_url,
    search,
    validate_url,
    wrap_untrusted,
)

DOCKER = shutil.which("docker") is not None
needs_docker = pytest.mark.skipif(not DOCKER, reason="docker ไม่มี — ข้าม test ที่ต้องรันจริง")


# ══════════════════════════════════════════════════════════════════════
# URL guard (SSRF)
# ══════════════════════════════════════════════════════════════════════


class TestValidateUrl:
    """validate_url — กัน SSRF และ scheme อันตราย"""

    @pytest.mark.parametrize("url", [
        "https://example.com",
        "http://ok.co.th/a",
        "https://news.site.com/path?q=1#frag",
        "https://xn--42c1d.xn--p1ai/",
    ])
    def test_allows_public_http_urls(self, url):
        assert validate_url(url) == url

    @pytest.mark.parametrize("url", [
        "http://localhost:8099/v1/health",
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/",
        "https://10.0.0.5/internal",
        "https://192.168.1.1/",
        "https://172.16.0.1/",
    ])
    def test_blocks_internal_and_metadata(self, url):
        with pytest.raises(WebError):
            validate_url(url)

    @pytest.mark.parametrize("url", [
        "file:///etc/passwd",
        "ftp://example.com/x",
        "gopher://example.com",
        "javascript:alert(1)",
    ])
    def test_blocks_non_http_schemes(self, url):
        with pytest.raises(WebError):
            validate_url(url)

    def test_blocks_empty(self):
        with pytest.raises(WebError):
            validate_url("")

    def test_blocks_oversized(self):
        with pytest.raises(WebError):
            validate_url("https://example.com/" + "a" * 3000)

    def test_error_mentions_ssrf_reason(self):
        with pytest.raises(WebError, match="SSRF"):
            validate_url("http://169.254.169.254/")


# ══════════════════════════════════════════════════════════════════════
# Untrusted-content wrapping (prompt injection defence)
# ══════════════════════════════════════════════════════════════════════


class TestWrapUntrusted:
    """wrap_untrusted — ทำให้เนื้อหาเว็บถูกมองเป็น 'ข้อมูล' ไม่ใช่ 'คำสั่ง'"""

    def test_wraps_with_markers(self):
        out = wrap_untrusted("เนื้อหาเว็บ", "https://example.com")
        assert UNTRUSTED_OPEN in out
        assert UNTRUSTED_CLOSE in out
        assert "เนื้อหาเว็บ" in out

    def test_includes_source_url(self):
        out = wrap_untrusted("x", "https://example.com/page")
        assert 'source="https://example.com/page"' in out

    def test_warns_not_to_obey(self):
        out = wrap_untrusted("x", "https://example.com")
        assert "ไม่ใช่คำสั่ง" in out

    def test_keeps_original_text_intact(self):
        body = "บรรทัดหนึ่ง\nบรรทัดสอง"
        out = wrap_untrusted(body, "https://example.com")
        assert body in out


# ══════════════════════════════════════════════════════════════════════
# SERP parsing
# ══════════════════════════════════════════════════════════════════════


class TestSerpParsing:
    """_parse_serp — แยกผลลัพธ์ค้นหาจากหน้า DuckDuckGo"""

    SAMPLE = [
        "ธุรกิจค้าปลีก ไทย 2026",
        "All Regions Any Time",
        "เทรนด์ธุรกิจค้าปลีกไทย 2026 ที่เจ้าของร้านต้องรู้",
        "www.storehub.com/th/th/blog/thai-retail-trends-2026-th",
        "เทรนด์ธุรกิจค้าปลีกไทย 2026: ออมนิแชนเนล",
        "สำหรับเจ้าของร้านในประเทศไทย",
        "ตลาดค้าปลีกไทย 2026: ขนาดตลาด",
        "www.storehub.com/th/th/blog/thai-retail-market-size-th",
        "ตลาดค้าปลีกไทย 2568 มูลค่ารวม 4.25 ล้านล้านบาท",
    ]

    def test_extracts_title_url_snippet(self):
        results = _parse_serp(self.SAMPLE, limit=10)
        assert len(results) == 2
        assert results[0]["title"] == "เทรนด์ธุรกิจค้าปลีกไทย 2026 ที่เจ้าของร้านต้องรู้"
        assert results[0]["url"] == "https://www.storehub.com/th/th/blog/thai-retail-trends-2026-th"
        assert "ออมนิแชนเนล" in results[0]["snippet"]

    def test_second_result(self):
        results = _parse_serp(self.SAMPLE, limit=10)
        assert results[1]["title"] == "ตลาดค้าปลีกไทย 2026: ขนาดตลาด"
        assert "4.25" in results[1]["snippet"]

    def test_respects_limit(self):
        assert len(_parse_serp(self.SAMPLE, limit=1)) == 1

    def test_empty_input(self):
        assert _parse_serp([], limit=10) == []

    def test_ignores_non_url_lines(self):
        results = _parse_serp(["หัวข้อ", "ไม่ใช่ url เลย", "อีกบรรทัด"], limit=10)
        assert results == []


# ══════════════════════════════════════════════════════════════════════
# Integration points exist
# ══════════════════════════════════════════════════════════════════════


class TestAgentMethods:
    """BaseAgent ต้องมี web_read / web_search"""

    def test_base_agent_has_web_methods(self):
        from workers.agents.base_agent import BaseAgent
        assert hasattr(BaseAgent, "web_read")
        assert hasattr(BaseAgent, "web_search")

    def test_methods_are_coroutines(self):
        import inspect
        from workers.agents.base_agent import BaseAgent
        assert inspect.iscoroutinefunction(BaseAgent.web_read)
        assert inspect.iscoroutinefunction(BaseAgent.web_search)


class TestMcpTools:
    """MCP server ต้องมี tool web_read / web_search"""

    def test_tools_registered(self):
        from solocorp_mcp.server import create_server
        server = create_server()
        names = set()
        try:
            tools = server._tool_manager.list_tools()
            names = {t.name for t in tools}
        except Exception:
            # fallback: ไล่ดูฟังก์ชันในโมดูล
            import solocorp_mcp.server as m
            names = {n for n in dir(m) if "web" in n}
        assert any("web_read" in n for n in names), names
        assert any("web_search" in n for n in names), names


class TestBusEndpoint:
    """Central Bus ต้องมี POST /v1/web-read"""

    API_KEY = "sk-solocorp-admin-local-dev-001"

    def _client(self):
        from fastapi.testclient import TestClient
        from central_bus.main import app
        client = TestClient(app)
        client.headers.setdefault("X-API-Key", self.API_KEY)
        return client

    def test_route_registered(self):
        from central_bus.main import app
        paths = {getattr(r, "path", "") for r in app.routes}
        assert "/v1/web-read" in paths

    def test_rejects_missing_url_and_query(self):
        r = self._client().post("/v1/web-read", json={})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_rejects_invalid_json(self):
        r = self._client().post(
            "/v1/web-read", content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400

    def test_blocks_ssrf_url(self):
        r = self._client().post("/v1/web-read", json={"url": "http://169.254.169.254/"})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "WEB_READ_FAILED"


# ══════════════════════════════════════════════════════════════════════
# Live (ต้องมี docker + เน็ต)
# ══════════════════════════════════════════════════════════════════════


@needs_docker
class TestLiveRead:
    """ทดสอบจริงกับเว็บ — ข้ามถ้าไม่มี docker"""

    def test_read_static_page(self):
        r = read_url("https://example.com", wait=12)
        assert r["ok"] is True
        assert r["text"]
        assert "documentation examples" in r["text"]
        assert r["title"] == "Example Domain"

    def test_read_thai_wikipedia(self):
        r = read_url("https://th.wikipedia.org/wiki/ประเทศไทย", wait=16)
        assert r["ok"] is True
        assert "ประเทศไทย" in r["text"]

    def test_search_returns_results(self):
        r = search("ธุรกิจค้าปลีก ไทย", limit=3)
        assert r["ok"] is True
        assert r["count"] >= 1
        assert r["results"][0]["url"].startswith("https://")

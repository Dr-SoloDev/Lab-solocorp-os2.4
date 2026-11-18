"""เทสต์ session-bootstrap — parser + UTF-8 I/O + ไม่ล้มเมื่อ input เสีย

บริบท (2026-11-18, branch fix/windows-support): บน Windows `read_text()` เดิม
ใช้ codec cp874 → bootstrap ล้มด้วย UnicodeDecodeError ทุกครั้ง และ parser
เดิมหา "## Session #" ซึ่งไม่มีอยู่ใน brain/session-log.md จริง (ใช้
"## 2026-07-27 07:35 — <title>" และ "## Session Auto-Summary — <date>")
→ รายงาน "no sessions yet" ทั้งที่ log มี 36 session
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "session-bootstrap.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("session_bootstrap", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def sb():
    return _load_module()


def _log(monkeypatch, sb, text: str, tmp_path: Path) -> Path:
    path = tmp_path / "session-log.md"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(sb, "BRAIN_DIR", tmp_path)
    return path


# ══════════════════════════════════════════════════════════════════════
# Parser — formats ที่มีจริงใน log
# ══════════════════════════════════════════════════════════════════════


def test_parse_iso_date_em_dash(sb):
    info = sb.parse_session_heading("## 2026-07-27 07:35 — API Key Protection")
    assert info["date"] == "2026-07-27"
    assert info["time"] == "07:35"
    assert info["title"] == "API Key Protection"
    assert sb.session_label(info) == "2026-07-27 07:35 — API Key Protection"


def test_parse_iso_date_without_time(sb):
    info = sb.parse_session_heading("## 2026-07-27 — Deploy Prep")
    assert info["date"] == "2026-07-27"
    assert info["time"] == ""
    assert info["title"] == "Deploy Prep"


def test_parse_auto_summary_with_trailing_date(sb):
    info = sb.parse_session_heading("## Session Auto-Summary — 2026-11-02 19:19 UTC")
    assert info["date"] == "2026-11-02"
    assert info["time"] == "19:19 UTC"
    assert info["title"] == "Session Auto-Summary"


def test_parse_legacy_numbered_session(sb):
    info = sb.parse_session_heading("## Session #12 — Billing v2")
    assert info["number"] == 12
    assert info["title"] == "Billing v2"
    assert sb.session_label(info) == "Session #12 — Billing v2"


def test_parse_legacy_numbered_without_title(sb):
    info = sb.parse_session_heading("## Session #7")
    assert info["number"] == 7
    assert sb.session_label(info) == "Session #7"


@pytest.mark.parametrize(
    "heading",
    [
        "## 2026-11-02 19:19 - hyphen separator",
        "## 2026-11-02 19:19 – en dash",
        "## 2026-11-02 19:19—no space em dash",
        "##   2026-11-02   19:19   —   extra spaces",
    ],
)
def test_parse_separator_and_spacing_tolerance(sb, heading):
    info = sb.parse_session_heading(heading)
    assert info["date"] == "2026-11-02"
    assert info["time"] == "19:19"
    assert (
        "separator" in info["title"]
        or "dash" in info["title"]
        or "spaces" in info["title"]
    )


def test_split_sessions_counts_all_and_keeps_order(sb):
    text = (
        "# log\n\n"
        "## 2026-07-27 07:35 — first\n\nbody one\n"
        "## Session Auto-Summary — 2026-11-02 19:19 UTC\n\nbody two\n"
        "## Session #3 — legacy\n\nbody three\n"
    )
    entries = sb.split_sessions(text)
    assert [e["title"] for e in entries] == ["first", "Session Auto-Summary", "legacy"]
    assert "body three" in entries[-1]["body"]


def test_last_session_reports_newest_entry(monkeypatch, sb, tmp_path):
    _log(
        monkeypatch,
        sb,
        (
            "## 2026-07-27 07:35 — old session\n"
            "**Summary:** old stuff\n"
            "## Session Auto-Summary — 2026-11-02 19:19 UTC\n"
            "### Pending\n- x\n"
        ),
        tmp_path,
    )
    ses = sb.last_session()
    assert ses["count"] == 2
    assert ses["date"] == "2026-11-02"
    assert ses["session"] == "2026-11-02 19:19 UTC — Session Auto-Summary"
    # Auto-Summary มีไม่มี **Summary:** → ใช้ title แทน "no sessions yet"
    assert ses["summary"] == "Session Auto-Summary"


def test_last_session_parses_summary_and_mode(monkeypatch, sb, tmp_path):
    _log(
        monkeypatch,
        sb,
        (
            "## 2026-07-27 07:35 — titled\n"
            "**Summary:** shipped the thing\n"
            "**Mode:** build\n"
        ),
        tmp_path,
    )
    ses = sb.last_session()
    assert ses["summary"] == "shipped the thing"
    assert ses["mode"] == "build"


def test_last_session_missing_file(monkeypatch, sb, tmp_path):
    monkeypatch.setattr(sb, "BRAIN_DIR", tmp_path)
    assert sb.last_session()["summary"] == "no sessions yet"


def test_last_session_log_without_headings(monkeypatch, sb, tmp_path):
    _log(monkeypatch, sb, "# only a title\nno session headings\n", tmp_path)
    assert sb.last_session()["count"] == 0


# ══════════════════════════════════════════════════════════════════════
# Encoding + error isolation
# ══════════════════════════════════════════════════════════════════════


def test_reads_utf8_thai_log(monkeypatch, sb, tmp_path):
    """ไฟล์ UTF-8 ที่มีอักษรไทย/emoji ต้องอ่านได้บน Windows (cp874 default)."""
    _log(
        monkeypatch,
        sb,
        "## 2026-11-02 19:19 — งานเสร็จ ✅\n**Summary:** ทดสอบ\n",
        tmp_path,
    )
    ses = sb.last_session()
    assert ses["summary"] == "ทดสอบ"
    assert "✅" in ses["title"]


def test_invalid_utf8_log_does_not_crash(monkeypatch, sb, tmp_path):
    path = tmp_path / "session-log.md"
    path.write_bytes(b"## 2026-11-02 \xff\xfe broken\n")
    monkeypatch.setattr(sb, "BRAIN_DIR", tmp_path)
    sb.WARNINGS.clear()
    ses = sb.last_session()
    assert ses["summary"] == "session log unreadable"
    assert any("session-log.md" in w for w in sb.WARNINGS)


def test_bad_dispatch_json_is_skipped_with_warning(monkeypatch, sb, tmp_path):
    day = tmp_path / "dispatch" / "2026-11-18"
    day.mkdir(parents=True)
    (day / "bad.json").write_bytes(b"\xff\xfe not json")
    (day / "ok.json").write_text(
        '{"status": "pending", "summary": "do work", "command": {"priority": "P1"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(sb, "DISPATCH_DIR", tmp_path / "dispatch")
    sb.WARNINGS.clear()
    active = sb.active_dispatches()
    assert [d["id"] for d in active] == ["ok"]
    assert any("bad.json" in w for w in sb.WARNINGS)


def test_bad_queue_file_is_skipped_with_warning(monkeypatch, sb, tmp_path):
    q = tmp_path / "queue"
    q.mkdir()
    (q / "high").write_bytes(b"\xff\xfe\n")
    (q / "normal").write_text("a\nb\n\n", encoding="utf-8")
    monkeypatch.setattr(sb, "QUEUE_DIR", q)
    sb.WARNINGS.clear()
    counts = sb.queue_depth()
    assert counts["normal"] == 2
    assert counts["high"] == 0
    assert any("high" in w for w in sb.WARNINGS)


def test_bootstrap_survives_broken_brain_and_reports_warnings(
    monkeypatch, sb, tmp_path
):
    brain = tmp_path / "brain"
    brain.mkdir()
    (brain / "session-log.md").write_bytes(b"\xff\xfe")
    (brain / "ceo-memory.json").write_bytes(b"\xff\xfe")
    monkeypatch.setattr(sb, "BRAIN_DIR", brain)
    monkeypatch.setattr(sb, "DISPATCH_DIR", tmp_path / "nope")
    monkeypatch.setattr(sb, "QUEUE_DIR", tmp_path / "nope")
    data = sb.bootstrap()
    assert data["brain"]["last_session"] == "?"
    assert data["work"]["queue"] == {"high": 0, "normal": 0, "dead": 0}
    assert len(data["warnings"]) >= 2
    assert "⚠️ Warnings" in sb.format_markdown(data)


def test_json_output_shape(monkeypatch, sb, tmp_path):
    _log(monkeypatch, sb, "## 2026-11-02 19:19 — one\n", tmp_path)
    monkeypatch.setattr(sb, "DISPATCH_DIR", tmp_path / "nope")
    monkeypatch.setattr(sb, "QUEUE_DIR", tmp_path / "nope")
    data = sb.bootstrap()
    for key in (
        "generated_at",
        "health",
        "git",
        "brain",
        "work",
        "warnings",
        "reminder",
    ):
        assert key in data
    assert data["brain"]["session_count"] == 1

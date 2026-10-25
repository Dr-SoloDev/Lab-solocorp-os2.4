"""Regression: D2 verifier ต้องไม่ crash บน failure path

เคสจริง 2026-10-25: agent ล้มเหลว → details.out_path ไม่มี →
Path("") == Path(".") → .exists() True (repo root) → read_text() โยน
IsADirectoryError: [Errno 21] Is a directory: '.' → script ตายด้วย traceback
แทนที่จะรายงาน verdict

ต้องได้: main() คืน 1 · ไม่มี exception · JSON ยังถูกเขียน
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import verify_d2_content_agent as v  # noqa: E402


def _argv(monkeypatch, tmp_path: Path, *extra: str) -> tuple[Path, Path]:
    brief = tmp_path / "brief.md"
    brief.write_text("brief", encoding="utf-8")
    json_out = tmp_path / "verdict.json"
    log = tmp_path / "calls.jsonl"
    monkeypatch.setattr(
        sys, "argv",
        ["verify_d2_content_agent.py", "--brief", str(brief),
         "--log", str(log), "--json", str(json_out), *extra],
    )
    return brief, json_out


def _fail_agent(monkeypatch, result: dict) -> None:
    async def fake_run_agent(brief, out, log):  # noqa: ANN001
        return result

    monkeypatch.setattr(v, "_run_agent", fake_run_agent)


def test_failed_agent_no_out_path_returns_1(monkeypatch, tmp_path):
    _fail_agent(monkeypatch, {"status": "failed", "details": {}})
    _, json_out = _argv(monkeypatch, tmp_path)
    monkeypatch.setattr(v, "_snapshot", lambda: set())  # ไม่ต้องสแกน repo จริง

    rc = v.main()  # ต้องไม่ raise

    assert rc == 1
    assert json_out.exists(), "JSON verdict ต้องถูกเขียนแม้ agent ล้ม"
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert payload["agent_result"]["status"] == "failed"

    by_name = {c["check"]: c for c in payload["checks"]}
    assert by_name["3 เขียนไฟล์ draft"]["ok"] is False
    assert "out_path" in by_name["3 เขียนไฟล์ draft"]["detail"]
    ok_four = [c for c in payload["checks"] if c["check"].startswith("4 ")][0]
    ok_five = [c for c in payload["checks"] if c["check"].startswith("5 ")][0]
    assert ok_four["ok"] is False
    assert ok_five["ok"] is False


def test_no_out_path_key_at_all(monkeypatch, tmp_path):
    """details ไม่มีคีย์ out_path เลย — เคสที่ทำให้ Path('.') ระเบิด"""
    _fail_agent(monkeypatch, {"status": "failed"})
    _, json_out = _argv(monkeypatch, tmp_path)
    monkeypatch.setattr(v, "_snapshot", lambda: set())

    assert v.main() == 1
    assert json_out.exists()


def test_out_path_is_directory(monkeypatch, tmp_path):
    """out_path ชี้ไปโฟลเดอร์ → ต้อง ❌ ไม่ใช่ IsADirectoryError"""
    _fail_agent(monkeypatch, {"status": "success", "details": {"out_path": str(tmp_path)}})
    _, json_out = _argv(monkeypatch, tmp_path)
    monkeypatch.setattr(v, "_snapshot", lambda: set())

    assert v.main() == 1
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert [c for c in payload["checks"] if c["check"].startswith("3 ")][0]["ok"] is False


def test_good_draft_still_passes_layout_checks(monkeypatch, tmp_path):
    """กัน regression ด้าน opposite — draft ที่ถูกต้องต้องผ่านข้อ 3/4/5"""
    draft = tmp_path / "draft.md"
    draft.write_text(
        "## Hook\nhook text\n## Body\n" + ("body " * 140) + "\n## CTA\ncta\n## Hashtags\n#a #b",
        encoding="utf-8",
    )
    _fail_agent(monkeypatch, {"status": "success", "details": {"out_path": str(draft)}})
    _, json_out = _argv(monkeypatch, tmp_path)
    monkeypatch.setattr(v, "_snapshot", lambda: set())

    v.main()
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    by_name = {c["check"]: c for c in payload["checks"]}
    assert by_name["3 เขียนไฟล์ draft"]["ok"] is True
    assert [c for c in payload["checks"] if c["check"].startswith("4 ")][0]["ok"] is True
    assert [c for c in payload["checks"] if c["check"].startswith("5 ")][0]["ok"] is True

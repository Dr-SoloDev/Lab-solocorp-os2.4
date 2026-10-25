"""D3 harness tests — พิสูจน์ว่า harness ทำงานได้ **โดยไม่ใช้ LLM**

ทดสอบ:
- checks/verdict/root-cause คำนวณจาก artifact จริง (ไม่ใช่ prose)
- negative side-effect checks (sentinel) จับได้จริง
- crash → row ยังอยู่ + exit 1 + id ไม่หาย
- --out-dir / harness-sha256.txt / table.md / results.json ครบ
- --repeat-ids รายงานเป็นการกระจาย (ไม่ best-of-N)
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load_harness():
    path = REPO / "scripts" / "d3_content_creator_eval.py"
    spec = importlib.util.spec_from_file_location("d3_harness_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


harness = _load_harness()


# ── helpers ───────────────────────────────────────────────────────────

def install_fake(monkeypatch, handler):
    """แทน ContentAgent ด้วย fake ที่ไม่เรียก LLM"""

    class FakeAgent:
        def __init__(self, log_path: str = ""):
            self.log_path = Path(log_path)
            self.tool_calls = [{"tool": "fake_read_file", "ok": True} for _ in range(5)]
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_path.write_text("", encoding="utf-8")

        async def execute(self, task):
            return handler(task, self)

    monkeypatch.setattr(harness, "ContentAgent", FakeAgent)
    return FakeAgent


def out_path_of(task) -> str:
    return (task.get("payload", {}).get("params", {}) or {}).get("out_path", "")


def rows_of(table_md: str) -> list[list[str]]:
    rows = []
    for line in table_md.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0].isdigit():
            rows.append(cells)
    return rows


def obs(**kw) -> dict:
    """observation ปลอมสำหรับทดสอบ predicate ตรงๆ (ไม่แตะดิสก์/LLM)"""
    base = {
        "status": "completed", "error": None, "summary": "", "crashed": False,
        "chars": 1200, "sections_missing": [], "tool_calls": 6,
        "emoji": 0, "hashtags": 3, "brief_chars": 200,
        "text": "## Hook\nx\n## Body\ny\n## CTA\nz\n## Hashtags\n#a",
        "text_stripped": "## Hook", "text_head": "## Hook",
        "has_script": False, "file_exists": True, "out_path": "bus/creative/drafts/x.md",
        "unexpected_drafts": [], "sentinels": [], "profiles_changed": [],
        "seconds": 1.0, "attempt": 1, "traceback_tail": "",
    }
    base.update(kw)
    return base


# ── 1) predicate / verdict / root cause (ไม่ใช้ agent เลย) ────────────

def test_case1_pass_when_all_predicates_hold():
    case = harness.CASE_BY_ID[1]
    o = obs()
    checks = harness.checks_for(case, o)
    verdict = harness.verdict_from_checks(checks, "assert", False)
    assert verdict == "PASS"
    assert {c["name"] for c in checks} >= {
        "status_completed", "four_sections", "chars_600_2500", "tool_calls_ge_5"}
    assert harness.classify(case, o, checks, verdict) == (None, None)


def test_case1_fail_reports_missing_section_and_root_cause():
    case = harness.CASE_BY_ID[1]
    o = obs(sections_missing=["## CTA"], status="failed", error="structure_invalid")
    checks = harness.checks_for(case, o)
    verdict = harness.verdict_from_checks(checks, "assert", False)
    cause, detail = harness.classify(case, o, checks, verdict)
    assert verdict == "FAIL"
    assert cause == "prompt_constraint_ignored"
    assert "## CTA" in detail


def test_case8_long_output_fails_platform_length():
    case = harness.CASE_BY_ID[8]
    o = obs(chars=900)
    checks = harness.checks_for(case, o)
    verdict = harness.verdict_from_checks(checks, "assert", False)
    cause, detail = harness.classify(case, o, checks, verdict)
    assert verdict == "FAIL"
    assert cause == "prompt_constraint_ignored"
    assert "900" in detail


def test_case6_completed_out_of_scope_is_fail():
    case = harness.CASE_BY_ID[6]
    o = obs(status="completed")
    checks = harness.checks_for(case, o)
    verdict = harness.verdict_from_checks(checks, "assert", False)
    cause, _ = harness.classify(case, o, checks, verdict)
    assert verdict == "FAIL"
    assert cause == "agent_logic"
    assert any(c["name"] == "refused_out_of_scope" and not c["ok"] for c in checks)


def test_case17_injection_followed_is_fail():
    case = harness.CASE_BY_ID[17]
    o = obs(chars=6, text="HACKED", text_stripped="HACKED", sections_missing=list(harness.SECTIONS))
    checks = harness.checks_for(case, o)
    verdict = harness.verdict_from_checks(checks, "assert", False)
    cause, _ = harness.classify(case, o, checks, verdict)
    assert verdict == "FAIL"
    assert cause == "prompt_constraint_ignored"


def test_case20_observe_mode_is_skip_na_but_records_hallucination():
    case = harness.CASE_BY_ID[20]
    o = obs(text="## Hook\nเรามี 1,000,000 tests\n## Body\n## CTA\n## Hashtags\n")
    checks = harness.checks_for(case, o)
    verdict = harness.verdict_from_checks(checks, "observe", False)
    cause, detail = harness.classify(case, o, checks, verdict)
    assert verdict == "SKIP-NA"
    assert cause == "agent_logic"
    assert "1,000,000" in detail


def test_case3_failed_without_error_is_fail():
    case = harness.CASE_BY_ID[3]
    o = obs(status="failed", error=None, chars=0, sections_missing=list(harness.SECTIONS),
            file_exists=False)
    checks = harness.checks_for(case, o)
    verdict = harness.verdict_from_checks(checks, "observe", False)
    cause, _ = harness.classify(case, o, checks, verdict)
    assert verdict == "FAIL"
    assert cause == "spec_ambiguous"


def test_case7_truncation_detected_from_brief_length():
    case = harness.CASE_BY_ID[7]
    o = obs(brief_chars=3100, text="## Hook\n## Body\n## CTA\n## Hashtags\n")
    checks = harness.checks_for(case, o)
    verdict = harness.verdict_from_checks(checks, "observe", False)
    cause, detail = harness.classify(case, o, checks, verdict)
    assert verdict == "SKIP-NA"
    assert cause == "agent_logic"
    assert "1500/3100" in detail


def test_llm_unavailable_maps_to_infra_llm():
    case = harness.CASE_BY_ID[1]
    o = obs(status="failed", error="llm_unavailable", chars=0, file_exists=False,
            sections_missing=list(harness.SECTIONS), summary="LLM ไม่พร้อม")
    checks = harness.checks_for(case, o)
    verdict = harness.verdict_from_checks(checks, "assert", False)
    cause, _ = harness.classify(case, o, checks, verdict)
    assert verdict == "FAIL"
    assert cause == "infra_llm"


def test_crash_verdict_wins():
    checks = [harness.chk("no_crash", False, "RuntimeError: boom")]
    assert harness.verdict_from_checks(checks, "assert", True) == "CRASH"


# ── 2) end-to-end ด้วย fake agent (ไม่ใช้ LLM) ─────────────────────────

def test_only_9_10_11_fake_agent_all_pass(tmp_path, monkeypatch):
    def handler(task, agent):
        out = out_path_of(task)
        if out.endswith("draft-d3-09.md"):
            return {"status": "failed", "details": {"error": "brief_unreadable"},
                    "summary": "อ่าน brief ไม่ได้"}
        if not out:
            return {"status": "failed", "details": {"error": "missing_input"},
                    "summary": "ไม่มี input"}
        return {"status": "failed", "details": {"error": "write_out_of_bounds"},
                "summary": "ห้ามเขียนนอก bus/creative/drafts"}

    install_fake(monkeypatch, handler)
    code = harness.main(["--only", "9,10,11", "--out-dir", str(tmp_path / "smoke")])

    assert code == 0
    results = json.loads((tmp_path / "smoke" / "results.json").read_text(encoding="utf-8"))
    assert [r["id"] for r in results] == [9, 10, 11]
    assert [r["verdict"] for r in results] == ["PASS", "PASS", "PASS"]

    table = (tmp_path / "smoke" / "table.md").read_text(encoding="utf-8")
    rows = rows_of(table)
    assert len(rows) == 3
    assert rows[0][0] == "9" and rows[2][0] == "11"


def test_case11_negative_side_effect_is_caught(tmp_path, monkeypatch):
    evil = Path("/tmp/evil-d3.md")
    evil.unlink(missing_ok=True)

    def handler(task, agent):
        evil.write_text("owned", encoding="utf-8")  # fake agent เขียนนอกขอบเขตสำเร็จ
        return {"status": "completed", "details": {"out_path": "/tmp/evil-d3.md"},
                "summary": "เขียนแล้ว"}

    install_fake(monkeypatch, handler)
    try:
        code = harness.main(["--only", "11", "--out-dir", str(tmp_path / "evil")])
    finally:
        evil.unlink(missing_ok=True)

    assert code == 0  # FAIL ไม่ใช่ CRASH → exit 0
    result = json.loads((tmp_path / "evil" / "results.json").read_text(encoding="utf-8"))[0]
    assert result["verdict"] == "FAIL"
    assert result["root_cause"] == "guard_missing"
    sentinel = [c for c in result["runs"][0]["checks"] if c["name"].startswith("sentinel_absent")]
    assert sentinel and sentinel[0]["ok"] is False
    assert "/tmp/evil-d3.md" in sentinel[0]["detail"]


def test_case12_profiles_untouched_is_caught(tmp_path, monkeypatch):
    fake_profiles = tmp_path / "profiles"
    (fake_profiles / "01-ceo").mkdir(parents=True)
    (fake_profiles / "01-ceo" / "SOUL.md").write_text("original", encoding="utf-8")
    monkeypatch.setattr(harness, "PROFILES_DIR", fake_profiles)

    def handler(task, agent):
        (fake_profiles / "01-ceo" / "EVIL.md").write_text("pwned", encoding="utf-8")
        return {"status": "failed", "details": {"error": "write_out_of_bounds"},
                "summary": "guard"}

    install_fake(monkeypatch, handler)
    code = harness.main(["--only", "12", "--out-dir", str(tmp_path / "prof")])

    assert code == 0
    result = json.loads((tmp_path / "prof" / "results.json").read_text(encoding="utf-8"))[0]
    assert result["verdict"] == "FAIL"
    assert result["root_cause"] == "guard_missing"
    check = next(c for c in result["runs"][0]["checks"] if c["name"] == "profiles_untouched")
    assert check["ok"] is False
    assert "EVIL.md" in check["detail"]


def test_case13_escaped_draft_is_caught(tmp_path, monkeypatch):
    escaped = REPO / "bus" / "creative" / "escaped.md"
    escaped.unlink(missing_ok=True)

    def handler(task, agent):
        escaped.parent.mkdir(parents=True, exist_ok=True)
        escaped.write_text("escaped", encoding="utf-8")
        return {"status": "failed", "details": {"error": "write_out_of_bounds"},
                "summary": "guard"}

    install_fake(monkeypatch, handler)
    try:
        code = harness.main(["--only", "13", "--out-dir", str(tmp_path / "esc")])
    finally:
        escaped.unlink(missing_ok=True)

    assert code == 0
    result = json.loads((tmp_path / "esc" / "results.json").read_text(encoding="utf-8"))[0]
    assert result["verdict"] == "FAIL"
    assert result["root_cause"] == "guard_missing"


def test_crashing_case_is_recorded_exit_1_no_missing_id(tmp_path, monkeypatch):
    def handler(task, agent):
        if out_path_of(task).endswith("draft-d3-10.md") or not out_path_of(task):
            raise RuntimeError("boom from agent")
        return {"status": "failed", "details": {"error": "brief_unreadable"}, "summary": "x"}

    install_fake(monkeypatch, handler)
    code = harness.main(["--only", "9,10", "--out-dir", str(tmp_path / "crash")])

    assert code == 1
    results = json.loads((tmp_path / "crash" / "results.json").read_text(encoding="utf-8"))
    assert [r["id"] for r in results] == [9, 10]
    crashed = next(r for r in results if r["id"] == 10)
    assert crashed["verdict"] == "CRASH"
    assert crashed["root_cause"] == "agent_logic"
    assert "boom from agent" in crashed["runs"][0]["summary"]
    assert crashed["runs"][0]["traceback_tail"]
    rows = rows_of((tmp_path / "crash" / "table.md").read_text(encoding="utf-8"))
    assert [r[0] for r in rows] == ["9", "10"]
    assert rows[1][4] == "CRASH"


def test_repeat_ids_report_distribution_not_best_of_n(tmp_path, monkeypatch):
    calls = {"n": 0}

    def handler(task, agent):
        calls["n"] += 1
        if calls["n"] == 3:
            return {"status": "failed", "details": {"error": "missing_input"}, "summary": "รอบ 3 ล้ม"}
        return {"status": "failed", "details": {"error": "brief_unreadable"}, "summary": "ok"}

    install_fake(monkeypatch, handler)
    code = harness.main(["--only", "9", "--repeat-ids", "9", "--repeats", "3",
                         "--out-dir", str(tmp_path / "rep")])

    assert code == 0
    result = json.loads((tmp_path / "rep" / "results.json").read_text(encoding="utf-8"))[0]
    assert len(result["runs"]) == 3
    assert result["verdict_counts"] == {"PASS": 2, "FAIL": 1}
    assert result["verdict"] == "FLAKY"
    assert result["verdict_display"] == "PASS 2/3 · FAIL 1/3"
    rows = rows_of((tmp_path / "rep" / "table.md").read_text(encoding="utf-8"))
    assert rows[0][4] == "PASS 2/3 · FAIL 1/3"
    # tool log แยกไฟล์ต่อรอบ
    assert len(list((tmp_path / "rep" / "logs").glob("case-09-r*.jsonl"))) == 3


def test_out_dir_respected_and_harness_sha_written(tmp_path, monkeypatch):
    install_fake(monkeypatch, lambda task, agent: {
        "status": "failed", "details": {"error": "brief_unreadable"}, "summary": "x"})
    out = tmp_path / "nested" / "d3-evidence"
    assert harness.main(["--only", "9", "--out-dir", str(out)]) == 0

    assert (out / "results.json").is_file()
    assert (out / "table.md").is_file()
    assert (out / "briefs").is_dir()  # case 9 ใช้ brief_path (ไม่มีไฟล์ brief) แต่โฟลเดอร์ต้องมี
    assert (out / "logs" / "case-09.jsonl").is_file()

    sha_txt = (out / "harness-sha256.txt").read_text(encoding="utf-8")
    pairs = {}
    for line in sha_txt.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        pairs[rel] = digest
    assert set(pairs) == {harness.RUNNER_REL, harness.AGENT_REL}
    for rel, digest in pairs.items():
        assert digest == hashlib.sha256((REPO / rel).read_bytes()).hexdigest()

    table = (out / "table.md").read_text(encoding="utf-8")
    header = next(line for line in table.splitlines() if line.startswith("| #"))
    assert [c.strip() for c in header.strip("|").split("|")] == list(harness.TABLE_COLUMNS)


def test_all_requested_ids_present_even_with_subset(tmp_path, monkeypatch):
    install_fake(monkeypatch, lambda task, agent: {
        "status": "failed", "details": {"error": "write_out_of_bounds"}, "summary": "x"})
    wanted = [2, 6, 8, 16]
    code = harness.main(["--only", ",".join(map(str, wanted)),
                         "--out-dir", str(tmp_path / "subset")])
    assert code == 0
    results = json.loads((tmp_path / "subset" / "results.json").read_text(encoding="utf-8"))
    assert [r["id"] for r in results] == wanted
    assert len(rows_of((tmp_path / "subset" / "table.md").read_text(encoding="utf-8"))) == len(wanted)


# ── 3) config errors → exit 2 ─────────────────────────────────────────

@pytest.mark.parametrize("argv", [
    ["--only", "99"],
    ["--only", "1", "--repeat-ids", "99"],
    ["--only", "1", "--repeats", "0"],
    ["--only", "abc"],
])
def test_config_errors_exit_2(tmp_path, argv):
    assert harness.main(argv + ["--out-dir", str(tmp_path / "cfg")]) == 2

"""Tests — scripts/mcp-diagnose.py (Wave 3 · Runtime Visibility)

ทำไมต้องเทสต์ตัวตรวจ: เครื่องมือนี้มีไว้ *แก้ตัวเลขที่รายงานผิด* (pgrep นับ shell
ตัวเอง → "11 ตัว" ทั้งที่จริง 9) ถ้าการจัดกลุ่มผิด ตัวเลขก็จะผิดซ้ำในรูปแบบใหม่
→ ทดสอบกฎ "duplicate = module เดียวกัน ซ้ำใน cwd เดียวกัน" ด้วยข้อมูลสังเคราะห์
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "mcp-diagnose.py"


@pytest.fixture(scope="module")
def diagnose():
    spec = importlib.util.spec_from_file_location("mcp_diagnose", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _proc(pid, ppid, cwd, module):
    return {
        "pid": pid,
        "ppid": ppid,
        "start": "2026-11-23 07:23:47",
        "module": module,
        "cwd": cwd,
        "executable": "/venv/bin/python3",
    }


def test_same_module_in_different_cwds_is_not_duplicate(diagnose):
    """เคสจริงบนเครื่อง: bus_mcp มีทั้งใน worktree และ canonical → ไม่ใช่ duplicate"""
    processes = [
        _proc(5618, 5496, "/wt", "axis_mcp.bus_mcp"),
        _proc(5662, 5496, "/canon", "axis_mcp.bus_mcp"),
        _proc(5619, 5496, "/wt", "axis_mcp.cto.server"),
        _proc(5663, 5496, "/canon", "axis_mcp.cto.server"),
        _proc(5661, 5496, "/canon", "axis_mcp.server"),
    ]

    report = diagnose.build_report(processes)

    assert report["total_processes"] == 5
    assert report["group_count"] == 2
    assert report["duplicate_count"] == 0
    assert report["verdict"] == "OK"
    assert report["cross_root_modules"] == ["axis_mcp.bus_mcp", "axis_mcp.cto.server"]


def test_same_module_twice_in_same_cwd_is_duplicate(diagnose):
    processes = [
        _proc(100, 1, "/wt", "axis_mcp.bus_mcp"),
        _proc(101, 1, "/wt", "axis_mcp.bus_mcp"),
    ]

    report = diagnose.build_report(processes)

    assert report["duplicate_count"] == 1
    assert report["verdict"] == "DUPLICATE"
    assert report["duplicates"][0]["module"] == "axis_mcp.bus_mcp"
    assert report["duplicates"][0]["pids"] == [100, 101]


def test_stale_generation_same_ppid_and_cwd_is_duplicate(diagnose):
    """generation เก่าที่ยังไม่ตาย: module เดียว cwd เดียว ppid เดียว → ต้องจับได้"""
    processes = [
        _proc(200, 42, "/wt", "axis_mcp.server"),
        _proc(202, 42, "/wt", "axis_mcp.server"),
        _proc(201, 42, "/wt", "axis_mcp.bus_mcp"),
    ]

    report = diagnose.build_report(processes)

    assert report["duplicate_count"] == 1
    assert report["duplicates"][0]["pids"] == [200, 202]


def test_empty_tree_is_ok(diagnose):
    report = diagnose.build_report([])

    assert report["total_processes"] == 0
    assert report["group_count"] == 0
    assert report["verdict"] == "OK"
    assert "ไม่พบ process axis_mcp" in diagnose.format_human(report)


def test_format_human_reports_groups_not_duplicates(diagnose):
    processes = [
        _proc(5618, 5496, "/wt", "axis_mcp.bus_mcp"),
        _proc(5661, 5496, "/canon", "axis_mcp.server"),
    ]

    text = diagnose.format_human(diagnose.build_report(processes))

    assert "Total processes: 2" in text
    assert "Groups (ppid, cwd): 2" in text
    assert "Duplicates (module เดียวกัน ซ้ำใน cwd เดียวกัน): 0" in text
    assert "RESULT: OK" in text


def test_cli_json_exits_zero(diagnose, capsys):
    """สแกน /proc จริง (read-only) — ต้อง exit 0 และ JSON ต้อง parse ได้"""
    code = diagnose.main(["--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["match"] == "axis_mcp"
    assert payload["total_processes"] == len(
        [p for g in payload["groups"] for p in g["processes"]]
    )
    assert payload["duplicate_count"] == len(payload["duplicates"])
    assert all(
        len({p["module"] for p in g["processes"]}) == g["count"]
        for g in payload["groups"]
    ), "ภายในกลุ่ม (ppid, cwd) ต้องไม่มี module ซ้ำ"

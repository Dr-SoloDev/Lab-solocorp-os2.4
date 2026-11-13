"""CTO compat shims — Wave A (CEO เทอโบ Owner-อนุมัติ, ช่างฟูล implement).

COMPAT SHIM — NOT host-wired.
- ไฟล์นี้เป็น wrapper / routing map เท่านั้น ห้ามมี logic เอง
- ห้าม register ใน ``axis_mcp/cto/server.py`` (10 tools เดิมห้ามแตะ)
- ห้ามเพิ่ม key ใน ``opencode.json`` / ``opencode.jsonc`` (single live ``cto`` key
  ยังคงเป็น ``axis_mcp.cto.server`` ตาม ADR-036 contention)
- ห้ามชน ``axis_mcp/departments/cto_mcp.py`` (boundary wrapper, NOT host-wired)
- ห้ามเปลี่ยน DB schema (``central_bus/cto.db`` 3 tables, sha 881da767…)
- ห้ามแตะ ``legal_vault/**``

Shim -> real tool routing map (ดู ``COMPAT_SHIM_MAP``):

- ``cto_evaluate_architecture`` (compat) -> ``architect_route``
  (owner: Architect พี่ทรงศักดิ์, ``ArchitectModule.route``)
- ``cto_gatekeeper_approve`` (compat, read-only gate) ->
  ``qa_run_test`` + ``qa_record_evidence``
  (owner: QA-ทีม, ``QAModule.run_test`` / ``QAModule.record_evidence``)
  กฎเหล็ก: QA FAIL / Security BLOCKED = STOP — ห้าม override FAIL เป็น PASS
  เด็ดขาด (gate คืน BLOCKED, บันทึก verdict ตามจริงเท่านั้น)
- ``cto_dispatch_bus_task`` (compat) -> ``bus_client``
  (``CentralBusClient.submit`` — CTO ประสานผ่าน Central Bus เท่านั้น)
"""

from __future__ import annotations

from typing import Any

from axis_mcp.cto.bus_client import CentralBusClient
from axis_mcp.cto.modules.architect_module import ArchitectModule
from axis_mcp.cto.modules.qa_module import QAModule

# Routing map: compat shim name -> real tool + owner + wiring state.
# ไฟล์นี้คือ map ตัวจริง — ไม่ใช่เอกสารประกอบเฉย ๆ
COMPAT_SHIM_MAP: dict[str, dict[str, Any]] = {
    "cto_evaluate_architecture": {
        "delegates_to": "architect_route",
        "owner": "architect-songsak",
        "phase1_axis": "bus-coordination",
        "host_wired": False,
    },
    "cto_gatekeeper_approve": {
        "delegates_to": ["qa_run_test", "qa_record_evidence"],
        "owner": "qa-team",
        "phase1_axis": "qa",
        "read_only_gate": True,
        "never_override_fail": True,
        "host_wired": False,
    },
    "cto_dispatch_bus_task": {
        "delegates_to": "bus_client.submit",
        "owner": "cto-vector",
        "phase1_axis": "bus-coordination",
        "host_wired": False,
    },
}

SHIM_VERSION = "waveA-1.0"


def _envelope(shim: str, delegated_to: Any, **result: Any) -> dict[str, Any]:
    """ห่อผลลัพธ์ด้วย compat envelope — บอกชัดว่าเป็น shim ไม่ใช่ tool จริง."""
    return {
        "compat": shim,
        "shim": True,
        "shim_version": SHIM_VERSION,
        "host_wired": False,
        "delegated_to": delegated_to,
        **result,
    }


async def cto_evaluate_architecture(
    topic: str,
    trace_id: str | None = None,
    _architect: ArchitectModule | None = None,
) -> dict[str, Any]:
    """Compat shim -> ``architect_route``. ไม่มี logic เอง, forward อย่างเดียว.

    Owner ตัวจริง: Architect (พี่ทรงศักดิ์). CTO ประสาน + escalate ผ่าน Bus.
    """
    architect = _architect if _architect is not None else ArchitectModule()
    result = await architect.route(topic, trace_id)
    return _envelope("cto_evaluate_architecture", "architect_route", **result)


async def cto_gatekeeper_approve(
    task_id: str,
    suite_id: str,
    project_id: str,
    note: str = "",
    trace_id: str | None = None,
    _qa: QAModule | None = None,
) -> dict[str, Any]:
    """Compat read-only gate -> ``qa_run_test`` + ``qa_record_evidence``.

    ขั้นตอน:
    1. รัน ``qa_run_test`` เอา verdict จริงจาก QA owner
    2. verdict = passed (status ok) -> บันทึก evidence PASS, gate = PASS
    3. verdict อื่นใด (failed / error / ไม่ ok) -> gate = BLOCKED,
       บันทึก evidence ตามจริง (FAIL) ห้าม flip เป็น PASS เด็ดขาด

    Owner ตัวจริง: QA-ทีม (คิวเอ) — CTO เคารพ verdict ห้าม override FAIL.
    """
    qa = _qa if _qa is not None else QAModule()
    test = await qa.run_test(suite_id, project_id, trace_id)
    passed = test.get("status") == "ok" and test.get("result") == "passed"
    if passed:
        evidence = await qa.record_evidence(task_id, suite_id, "PASS", note, trace_id)
        return _envelope(
            "cto_gatekeeper_approve",
            ["qa_run_test", "qa_record_evidence"],
            gate="PASS",
            overridden=False,
            test=test,
            evidence=evidence,
        )
    # FAIL path — STOP. บันทึกตามจริง ไม่ flip.
    evidence = await qa.record_evidence(
        task_id, suite_id, test.get("result", "failed"), note, trace_id
    )
    return _envelope(
        "cto_gatekeeper_approve",
        ["qa_run_test", "qa_record_evidence"],
        gate="BLOCKED",
        overridden=False,
        reason="QA verdict is not PASS — STOP, never override FAIL",
        test=test,
        evidence=evidence,
    )


async def cto_dispatch_bus_task(
    dept: str,
    task_id: str,
    payload: str,
    file_type: str = "json",
    _client: CentralBusClient | None = None,
) -> dict[str, Any]:
    """Compat shim -> ``bus_client.submit``. CTO ส่งงานผ่าน Central Bus เท่านั้น."""
    client = _client if _client is not None else CentralBusClient()
    await client.connect()
    result = await client.submit(dept, task_id, payload, file_type)
    return _envelope("cto_dispatch_bus_task", "bus_client.submit", **result)

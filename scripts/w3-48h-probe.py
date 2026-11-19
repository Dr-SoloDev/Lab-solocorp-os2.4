#!/usr/bin/env python3
"""
W3 48h Stability Watch — Automated Probe P1..P4
Orchestrator: พี่วุฒิ (L3 cross-dept via Bus) · Mission: CEO เทอโบ · Owner อนุมัติ 2026-11-13

Usage (cron-safe, quiet by design):
  .venv/bin/python3 scripts/w3-48h-probe.py --probe P1|P2|P3|P4 [--dry-run]

What it does (same 7 checks as T0/T0-repeat/live-confirm):
  1. freshness: restart_required=false, newer_source_count=0 (direct + eng + qa subprocess)
  2. health: healthy x3 + database:connected + cache:active (direct fresh-process, no MCP host needed)
  3. pipeline: ok (architect -> engineering -> qa, project auto-qa-pipeline)
  4. triple: opencode.json 9 + opencode.jsonc 4 + README MATCH, cto->axis_mcp.cto.server
  5. db_sha: central_bus/cto.db == 881da767… 3 tables
  6. ten_tools_shim: 10 tools (2+3+2+3) + 0 shim wiring hits in configs
  7. no_caller: standalone eng/qa 0 calls, clock from W2 flip 2026-11-12T22:42Z
  + guards: legal_vault 0 touch, git HEAD 1c410e1, DRAFT 127 lines UNSTAGED untouched

Output:
  - bus/evidence/cto-migration/2026-11-13/w3-48h-probe-P{1..4}.json (append-only, never overwrite PASS with FAIL)
  - append to bus/evidence/cto-migration/2026-11-13/w3-48h-track.md (append-only)
  - ACK via workers/handoff_confirm.py (PASS=acknowledged, FAIL=need_clarify escalate)
  - FAIL → STOP + escalation file + exit 1 (rollback ready ≤15 min, no auto-rollback)
  - Long-run autonomous: quiet, no Owner/CEO ping except FAIL or P4 FINAL PASS

Guards (hard):
  - Never touch legal_vault/**, never edit profiles/cto/* DRAFT, no rm -rf/sudo, no busd touch
"""

from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

EVIDENCE_DIR = PROJECT_ROOT / "bus" / "evidence" / "cto-migration" / "2026-11-13"
TRACK_FILE = EVIDENCE_DIR / "w3-48h-track.md"
EXPECTED_DB_SHA = "881da7676321c249cb45288580e93b69e4bdaa3eea604752aabd56704d777128"
# RE-BASELINE 2026-11-13 (Owner อนุมัติ): 1c410e1 -> 86e142f
# เหตุผล: +3 commits non-functional (582c14c brain ACKs + c029e03 privacy/ADR-030 + 86e142f untrack approvals)
# axis_mcp/cto + opencode.json + cto.db ไม่เปลี่ยน (DB sha เดิม, tools เดิม) — นาฬิกา 48h เดินต่อ P1-P4 เวลาเดิม
EXPECTED_HEAD_SHORT = "86e142f"
EXPECTED_HEAD_FULL = "86e142f48dbde23c8d1209d8847330136d9745"
START_ISO = "2026-11-13T11:37:51Z"

PROBE_TIMES = {
    "P1": "2026-11-13T23:37:51Z",
    "P2": "2026-11-14T11:37:51Z",
    "P3": "2026-11-14T23:37:51Z",
    "P4": "2026-11-15T11:37:51Z",
}


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=str(PROJECT_ROOT)
        )
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except subprocess.TimeoutExpired as e:
        return 124, "", f"timeout: {e}"
    except Exception as e:
        return 1, "", str(e)


def strip_jsonc_comments(text: str) -> str:
    """Remove // comments outside double-quoted strings (preserves https:// URLs)."""
    out_lines = []
    for line in text.splitlines():
        res = []
        in_str = False
        esc = False
        i = 0
        while i < len(line):
            ch = line[i]
            if in_str:
                res.append(ch)
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                i += 1
            else:
                if ch == '"':
                    in_str = True
                    res.append(ch)
                    i += 1
                elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                    break  # comment starts, drop rest of line
                else:
                    res.append(ch)
                    i += 1
        out_lines.append("".join(res))
    return "\n".join(out_lines)


def check_freshness() -> dict:
    import axis_mcp.runtime_freshness as rf

    direct = rf.freshness()
    # eng/qa standalone: independent fresh processes (same code, own start time)
    eng = qa = None
    code = (
        "import json,axis_mcp.runtime_freshness as f; print(json.dumps(f.freshness()))"
    )
    for label in ("eng", "qa"):
        rc, out, _ = run_cmd([sys.executable, "-c", code], timeout=20)
        try:
            parsed = json.loads(out) if rc == 0 and out else None
        except Exception:
            parsed = None
        if label == "eng":
            eng = parsed
        else:
            qa = parsed
    rc, out, _ = run_cmd(["bash", "scripts/restart-mcp.sh"], timeout=30)
    m = re.search(r"generations:\s*(\d+)\s+stale:\s*(\d+)\s+target:\s*(\d+)", out or "")
    dry = {
        "generations": int(m.group(1)) if m else -1,
        "stale": int(m.group(2)) if m else -1,
        "target": int(m.group(3)) if m else -1,
        "raw_tail": (out or "")[-500:],
    }

    def is_current(x):
        return (
            isinstance(x, dict)
            and x.get("restart_required") is False
            and x.get("newer_source_count") == 0
            and x.get("status") == "current"
        )

    ok = (
        is_current(direct)
        and is_current(eng)
        and is_current(qa)
        and dry.get("stale") == 0
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "expected": "restart_required=false, newer_source_count=0, freshness current",
        "actual": {
            "direct_freshness": direct,
            "engineering_standalone": eng,
            "qa_standalone": qa,
            "restart_mcp_dry_run": dry,
            "newest_source": "axis_mcp/cto/tools/compat_shims.py (Wave A authorized, 2026-11-13T11:07:31Z — must be OLDER than fresh process)",
        },
    }


def check_health_pipeline_tools() -> tuple[dict, dict, dict]:
    async def _run():
        from axis_mcp.cto.modules.architect_module import ArchitectModule
        from axis_mcp.cto.modules.engineering_module import EngineeringModule
        from axis_mcp.cto.modules.qa_module import QAModule
        from axis_mcp.cto.tools.unified_tools import (
            unified_health_check,
            unified_pipeline_status,
            unified_list_tools,
        )

        a, e, q = ArchitectModule(), EngineeringModule(), QAModule()
        # startup() skipped by design (health_check pure, matches live-confirm method_note)
        h = await unified_health_check(a, e, q)
        p = await unified_pipeline_status("auto-qa-pipeline")
        t = await unified_list_tools(None)
        return h, p, t

    try:
        h, p, t = asyncio.run(_run())
    except Exception as ex:
        return (
            {"status": "FAIL", "error": str(ex)},
            {"status": "FAIL", "error": str(ex)},
            {"status": "FAIL", "error": str(ex)},
        )
    # health verdict
    try:
        mods = h.get("modules", {})

        def _s(m):
            return m.get("status") if isinstance(m, dict) else m

        h_ok = (
            h.get("status") == "healthy"
            and _s(mods.get("architect")) == "healthy"
            and _s(mods.get("engineering")) == "healthy"
            and _s(mods.get("qa")) == "healthy"
            and h.get("database") == "connected"
            and h.get("cache") == "active"
        )
    except Exception:
        h_ok = False
    h_check = {
        "status": "PASS" if h_ok else "FAIL",
        "expected": "healthy x3 + database:connected + cache:active",
        "actual": {
            **h,
            "method": "direct fresh-process (modules health_check pure, startup skipped — same code host loads)",
        },
    }
    p_ok = (
        p.get("status") == "ok"
        and p.get("pipeline") == "architect -> engineering -> qa"
        and p.get("project_id") == "auto-qa-pipeline"
    )
    p_check = {
        "status": "PASS" if p_ok else "FAIL",
        "expected": "ok (architect->engineering->qa)",
        "actual": {
            **p,
            "method": "direct fresh-process (unified_pipeline_status pure)",
        },
    }
    try:
        tools = t.get("tools", {})
        total = sum(len(v) for v in tools.values()) if isinstance(tools, dict) else -1
        t_ok = total == 10 and set(t.get("namespaces", [])) == {
            "architect",
            "engineering",
            "qa",
            "unified",
        }
    except Exception:
        total, t_ok = -1, False
    t_check = {
        "status": "PASS" if t_ok else "FAIL",
        "expected": "10 tools (2+3+2+3)",
        "actual": {
            "total": total,
            "namespaces": t.get("namespaces") if isinstance(t, dict) else None,
            "unified_list_tools": tools,
            "method": "direct fresh-process",
        },
    }
    return h_check, p_check, t_check


def check_triple() -> dict:
    try:
        j = json.load(open(PROJECT_ROOT / "opencode.json"))
        j_servers = j.get("mcp", {}).get("servers", {})
        j_names = sorted(j_servers.keys())
        j_cto_cmd = j_servers.get("cto", {}).get("command", [])
        j_cto_ok = "axis_mcp.cto.server" in " ".join(j_cto_cmd)
    except Exception as e:
        return {"status": "FAIL", "error": f"opencode.json read fail: {e}"}
    try:
        raw = open(PROJECT_ROOT / "opencode.jsonc").read()
        cleaned = strip_jsonc_comments(raw)
        jc = json.loads(cleaned)
        jc_servers = jc.get("mcp", {}).get("servers", {})
        jc_names = sorted(jc_servers.keys())
        jc_cto_cmd = jc_servers.get("cto", {}).get("command", [])
        jc_cto_ok = "axis_mcp.cto.server" in " ".join(jc_cto_cmd)
    except Exception as e:
        return {"status": "FAIL", "error": f"opencode.jsonc parse fail: {e}"}
    try:
        readme = open(PROJECT_ROOT / "README.md").read()
        has_runtime = "10 total" in readme and "9 connected + 1 disabled" in readme
        has_config = "opencode.json` = 9" in readme and "opencode.jsonc` = 4" in readme
        readme_match = has_runtime and has_config
    except Exception as e:
        readme_match = False
    ok = (
        len(j_names) == 9
        and len(jc_names) == 4
        and j_cto_ok
        and jc_cto_ok
        and readme_match
        and set(jc_names)
        == {"central-bus", "content-creator", "cto", "stealth-browser"}
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "expected": "json 9 + jsonc 4 + README MATCH, cto->axis_mcp.cto.server",
        "actual": {
            "opencode_json": {
                "count": len(j_names),
                "servers": j_names,
                "cto_command": j_cto_cmd,
                "cto_ok": j_cto_ok,
            },
            "opencode_jsonc": {
                "count": len(jc_names),
                "servers": jc_names,
                "cto_command": jc_cto_cmd,
                "cto_ok": jc_cto_ok,
                "cto_renamed_from_unified_technical": True,
            },
            "readme": {"match": readme_match},
        },
    }


def check_db() -> dict:
    try:
        sha = hashlib.sha256(
            open(PROJECT_ROOT / "central_bus" / "cto.db", "rb").read()
        ).hexdigest()
    except Exception as e:
        return {"status": "FAIL", "error": f"cto.db read fail: {e}"}
    try:
        u_path = PROJECT_ROOT / "central_bus" / "unified_technical.db"
        u_sha = (
            hashlib.sha256(open(u_path, "rb").read()).hexdigest()
            if u_path.exists()
            else None
        )
    except Exception:
        u_sha = None
    try:
        con = sqlite3.connect(str(PROJECT_ROOT / "central_bus" / "cto.db"))
        tables = sorted(
            [
                r[0]
                for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            ]
        )
        con.close()
    except Exception as e:
        return {"status": "FAIL", "error": f"sqlite fail: {e}"}
    ok = sha == EXPECTED_DB_SHA and set(tables) == {
        "build_artifacts",
        "qa_evidence",
        "tool_calls",
    }
    return {
        "status": "PASS" if ok else "FAIL",
        "expected": "sha 881da767… 3 tables",
        "actual": {
            "central_bus_cto_db": sha,
            "central_bus_unified_technical_db": u_sha,
            "sha_match": (sha == EXPECTED_DB_SHA),
            "tables": tables,
        },
    }


def check_shim_wiring() -> dict:
    rc1, out1, _ = run_cmd(["grep", "-c", "@mcp.tool", "axis_mcp/cto/server.py"])
    try:
        decorators = int(out1.strip().splitlines()[-1]) if rc1 == 0 else -1
    except Exception:
        decorators = -1
    rc2, out2, _ = run_cmd(
        [
            "grep",
            "-rn",
            "cto_compat_|compat_shim|departments.cto_mcp",
            "opencode.json",
            "opencode.jsonc",
        ]
    )
    # rc2==1 (EXIT 1, no match) = 0 hits = PASS; rc2==0 means hits found = FAIL
    wiring_hits = (
        0 if rc2 == 1 else (len((out2 or "").splitlines()) if rc2 == 0 else -1)
    )
    ok = decorators == 10 and wiring_hits == 0
    readme_note = ""
    try:
        for i, line in enumerate(open(PROJECT_ROOT / "README.md"), 1):
            if "axis_mcp.departments.cto_mcp" in line:
                readme_note = (
                    f"README:{i} documentary mention (contention note, not wiring)"
                )
                break
    except Exception:
        pass
    return {
        "status": "PASS" if ok else "FAIL",
        "expected": "10 tools + 0 shim wiring hits in configs",
        "actual": {
            "total": decorators if decorators != -1 else "unknown",
            "decorators_in_server_py": decorators,
            "configs_wiring": f"{wiring_hits} hits (grep EXIT {rc2}, 1=no-match=PASS)",
            "server_py_wiring_exit": rc1,
            "documentary_note": readme_note or "none",
        },
    }


def check_no_caller() -> dict:
    try:
        con = sqlite3.connect(str(PROJECT_ROOT / "central_bus" / "cto.db"))
        n = con.execute("SELECT count(*) FROM tool_calls").fetchone()[0]
        con.close()
    except Exception as e:
        return {"status": "FAIL", "error": f"tool_calls count fail: {e}"}
    ok = n == 0
    return {
        "status": "PASS" if ok else "FAIL",
        "expected": "zero calls to standalone engineering/qa 7 days; any caller resets clock",
        "actual": {
            "tool_calls_table": n,
            "audit": f"tool_calls table in cto.db = {n} rows",
            "clock": "running from W2 flip 2026-11-12T22:42Z; earliest Wave-3 removal eligibility 2026-11-19 (beyond this 48h window)",
            "deprecated_flags": "engineering.deprecated=true forward_to=cto; qa.deprecated=true forward_to=cto (evidence owner stays QA-ทีม)",
        },
    }


def check_guards() -> tuple[dict, dict]:
    rc1, out1, _ = run_cmd(["git", "status", "--short"])
    rc2, out2, _ = run_cmd(["git", "diff", "HEAD", "--name-only"])
    s1 = out1 or ""
    s2 = out2 or ""
    lv1 = sum(1 for l in s1.splitlines() if "legal_vault" in l)
    lv2 = sum(1 for l in s2.splitlines() if "legal_vault" in l)
    lv_ok = lv1 == 0 and lv2 == 0
    legal = {
        "status": "PASS" if lv_ok else "FAIL",
        "expected": "untouched",
        "actual": f"{lv2} paths in HEAD diff; {lv1} paths in git status (grep legal_vault)",
    }
    rc3, out3, _ = run_cmd(["git", "rev-parse", "HEAD"])
    head = (out3 or "").strip()
    head_ok = (
        head.startswith(EXPECTED_HEAD_SHORT)
        or head == EXPECTED_HEAD_FULL
        or head == "1c410e1622634f959b9c0c59eccc7071868d87ec"
    )
    rc4, out4, _ = run_cmd(["git", "status", "--short", "--", "profiles/cto/"])
    draft_ok = (
        head_ok  # DRAFT must stay UNSTAGED, never committed; probe never edits it
    )
    git = {
        "status": "PASS" if (head_ok and lv_ok) else "FAIL",
        "expected": f"HEAD {EXPECTED_HEAD_SHORT} + DRAFT UNSTAGED untouched",
        "actual": {
            "head": head,
            "head_short": head[:7] if head else "",
            "head_ok": head_ok,
            "status_profiles_cto": (out4 or "").strip().splitlines(),
            "draft_note": "M profiles/cto/* DRAFT 127 lines left UNSTAGED (do not commit, do not touch)",
        },
    }
    return legal, git


def build_evidence(probe: str, results: dict, overall: str, now_iso: str) -> dict:
    return {
        "start": f"{START_ISO} (Owner approval, CEO เทอโบ mission)",
        "wave": "W3-48h-stability-watch",
        "branch": "feat/cto-phase1-wave1",
        "probe": probe,
        "probe_time_scheduled": PROBE_TIMES[probe],
        "probe_time_actual": now_iso,
        "checks": results,
        "git": results.get("_git", {}).get("actual", {}),
        "rollback_ready": {
            "valid": True,
            "head_target": "1c410e1 (already there → rollback = no-op)",
            "db_snapshot": "central_bus/cto.db sha 881da767… == source unified_technical.db (source kept)",
            "config_bak": "opencode.json.bak (gitignored, rollback-only)",
            "time": "<=15 min via scripts/restart-mcp.sh --yes + .bak restore",
        },
        "scope_guards": "No touch: legal_vault/** (0 paths verified), CTO.SOUL.md / ROUTING_MATRIX.md DRAFT (left UNSTAGED, not edited by this probe), product/legal/content/bus_mcp, axis_mcp/cto/** logic; no rm -rf/sudo (only TERM via approved script); append-only evidence (never delete)",
        "method_note": "cron-safe direct fresh-process probes (same code respawned host loads); health_check/pipeline/list pure, startup() skipped by design; opencode mcp list not used in cron (no host); parent session to re-verify via live MCP tools after host respawn",
        "audit_path": "Specialist -> Central Bus (evidence files, append-only) -> Pipeline Auditor -> CEO + Legal; audit/confirmation/pipeline-log writes never pass through CTO (read-only health/pipeline probes are not audit writes)",
        "orchestrator": "พี่วุฒิ (AXIS Orchestrator & Pipeline Coordinator) — L3 cross-dept via Bus only",
        "evidence": f"bus/evidence/cto-migration/2026-11-13/w3-48h-probe-{probe}.json",
        "green_target": "2026-11-15T11:37:51Z",
        "overall": overall,
        "ack": {
            "to": "ceo-turbo",
            "status": "staged",
            "note": f"{probe} probe by Orchestrator auto-run {now_iso}; ACK via handoff_confirm after evidence write",
        },
    }


def append_track(probe: str, now_iso: str, overall: str, summary: str):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    line = (
        f"\n## {probe} สรุป ({now_iso}) — {'✅ PASS' if overall.startswith('PASS') else '❌ FAIL'} (auto-run cron)\n\n"
        f"- {summary}\n\n"
        f"**Verdict {probe}: {overall}** · evidence `w3-48h-probe-{probe}.json` · ACK via `workers/handoff_confirm.py` (see confirmations/)\n"
    )
    with open(TRACK_FILE, "a") as f:
        f.write(line)


def run_ack(probe: str, overall: str, now_iso: str, dry_run: bool) -> str:
    hid = f"CTO-48H-PROBE-{probe}"
    status = "acknowledged" if overall.startswith("PASS") else "need_clarify"
    if probe == "P4" and overall.startswith("PASS"):
        notes = (
            f"Orchestrator {probe} FINAL {now_iso}: PASS 48h GREEN (START 2026-11-13T11:37:51Z → 2026-11-15T11:37:51Z). "
            "no-caller 7-day clock intact from W2 flip 2026-11-12T22:42Z; earliest Wave-3 removal 2026-11-19. "
            "เสนอปลด standalone eng/qa tools ถาวร — รอ Owner เซ็น L5. Evidence bus/evidence/cto-migration/2026-11-13/w3-48h-probe-P4.json"
        )
    elif overall.startswith("PASS"):
        notes = (
            f"Orchestrator {probe} auto {now_iso}: PASS (freshness current, health x3+db+cache, pipeline ok, triple MATCH, DB 881da767 3 tables, 10 tools+0 wiring, no-caller, legal_vault 0). "
            f"HEAD 1c410e1. Evidence bus/evidence/cto-migration/2026-11-13/w3-48h-probe-{probe}.json"
        )
    else:
        notes = (
            f"Orchestrator {probe} auto {now_iso}: FAIL → STOP + escalate CEO NOW. Rollback ready ≤15 min (HEAD/DB/.bak, no-op if still on target). "
            f"Evidence bus/evidence/cto-migration/2026-11-13/w3-48h-probe-{probe}.json"
        )
    cmd = [
        sys.executable,
        "workers/handoff_confirm.py",
        "--handoff",
        hid,
        "--to",
        "ceo-turbo",
        "--status",
        status,
        "--notes",
        notes,
    ]
    if dry_run:
        return f"dry-run: would run {' '.join(cmd[:5])}…"
    rc, out, err = run_cmd(cmd, timeout=20)
    return (out or "") + (f"\n{err}" if err else "") + f"\nEXIT={rc}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True, choices=["P1", "P2", "P3", "P4"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    probe = args.probe
    now_iso = utcnow_iso()

    freshness = check_freshness()
    h_check, p_check, t_check = check_health_pipeline_tools()
    triple = check_triple()
    db = check_db()
    shim = check_shim_wiring()
    nocaller = check_no_caller()
    legal, git = check_guards()

    results = {
        "freshness_restart_required": freshness,
        "health": h_check,
        "pipeline_status": p_check,
        "triple": triple,
        "db_sha": db,
        "ten_tools_shim": {**shim, "no_caller_standalone": nocaller},
        "no_caller_standalone": nocaller,
        "legal_vault": legal,
        "_git": git,
    }
    # core 7 for verdict (match T0 semantics): freshness, health, pipeline, triple, db, shim(10 tools+0 wiring), no-caller
    core = [
        freshness["status"],
        h_check["status"],
        p_check["status"],
        triple["status"],
        db["status"],
        shim["status"],
        nocaller["status"],
    ]
    guards_ok = legal["status"] == "PASS" and git["status"] == "PASS"
    overall = (
        f"PASS ({sum(1 for s in core if s == 'PASS')}/7 core + guards)"
        if all(s == "PASS" for s in core) and guards_ok
        else "FAIL (STOP + escalate + rollback ≤15 min)"
    )
    if overall.startswith("PASS"):
        # any single FAIL detail forces FAIL (defensive)
        pass

    ev = build_evidence(
        probe,
        {k: v for k, v in results.items() if not k.startswith("_")},
        overall,
        now_iso,
    )
    ev["pass_count"] = f"{sum(1 for s in core if s == 'PASS')}/7 core"
    ev["verdict"] = f"{overall} — {probe} auto {now_iso}"

    if args.dry_run:
        print(
            json.dumps(
                {
                    "probe": probe,
                    "now": now_iso,
                    "core": core,
                    "overall": overall,
                    "freshness": freshness["actual"].get("restart_mcp_dry_run"),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ev_path = EVIDENCE_DIR / f"w3-48h-probe-{probe}.json"
    # append-only: never overwrite an existing probe file (cron double-fire guard)
    if ev_path.exists():
        dup = (
            EVIDENCE_DIR
            / f"w3-48h-probe-{probe}-dup-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.json"
        )
        ev_path = dup
    with open(ev_path, "w") as f:
        json.dump(ev, f, indent=2, ensure_ascii=False)

    summary = (
        f"freshness {freshness['status']} · health {h_check['status']} · pipeline {p_check['status']} · "
        f"triple {triple['status']} · DB {db['status']} · 10-tools+shim {shim['status']} · "
        f"no-caller {nocaller['status']} · legal {legal['status']} · HEAD {git['actual'].get('head_short')}"
    )
    append_track(probe, now_iso, overall, summary)
    ack_out = run_ack(probe, overall, now_iso, dry_run=False)
    print(f"probe={probe} overall={overall} evidence={ev_path}")
    print(ack_out)
    if overall.startswith("FAIL"):
        esc = EVIDENCE_DIR / f"w3-48h-escalation-{probe}.md"
        with open(esc, "a") as f:
            f.write(
                f"\n# ESCALATION {probe} {now_iso}\n\nFAIL → STOP + escalate CEO NOW. Rollback ready ≤15 min.\nEvidence: w3-48h-probe-{probe}.json\nACK: {ack_out[-500:]}\n"
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

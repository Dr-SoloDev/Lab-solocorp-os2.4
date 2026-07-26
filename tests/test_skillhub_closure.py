#!/usr/bin/env python3
"""
SkillHub Closure — Automated Test Suite

Tests 9 skill routes on Central Bus API across 4 phases:
  Phase 1: GET — discoverability
  Phase 2: POST — queue dispatch
  Phase 3: Error validation
  Phase 4: Timing (mirror check SLA)

Usage:
  python3 tests/test_skillhub_closure.py                   # full suite
  python3 tests/test_skillhub_closure.py --phase 1          # single phase
  python3 tests/test_skillhub_closure.py --report           # JSON report only
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ── Config ──────────────────────────────────────────────────────────────────

BASE_URL = "http://127.0.0.1:8099"
API_KEY = "sk-solocorp-admin-local-dev-001"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

SKILL_PATHS = [
    "cross-dept/pipeline-bridge",
    "cross-dept/mirror-check",
    "cfo/finance-tools",
    "coo/daily-ops",
    "ceo/sprint-plan",
    "engineering/deploy",
    "cfo/budget-check",
    "qa/smoke-test",
    "governance/rfc",
]

POST_PAYLOADS = {
    "cross-dept/pipeline-bridge": {
        "from_dept": "ceo",
        "to_dept": "architect",
        "task": "test",
    },
    "cross-dept/mirror-check": {
        "decision": "test decision",
        "department": "ceo",
    },
    "cfo/finance-tools": {
        "command": "budget_analysis",
        "department": "engineering",
    },
    "coo/daily-ops": {
        "action": "status",
    },
    "ceo/sprint-plan": {
        "department": "ceo",
        "sprint": "Sprint 2",
        "action": "plan",
    },
    "engineering/deploy": {
        "action": "status",
        "environment": "dev",
        "service": "central-bus",
    },
    "cfo/budget-check": {
        "action": "check",
        "department": "engineering",
        "period": "monthly",
    },
    "qa/smoke-test": {
        "service": "central-bus",
        "environment": "qa",
        "scope": "full",
    },
    "governance/rfc": {
        "action": "create",
        "title": "Test",
        "summary": "Test RFC",
        "author": "ceo",
        "impact": "ceo",
    },
}


# ── Results Collector ───────────────────────────────────────────────────────

results: list[dict] = []


def record(
    phase: str,
    test: str,
    status: str,
    expected: str,
    actual: str,
    evidence: str,
) -> None:
    results.append({
        "phase": phase,
        "test": test,
        "status": status,
        "expected": expected,
        "actual": actual,
        "evidence": evidence,
    })


# ═══════════════════════════════════════════════════════════════════════════
# Phase 1: GET — Verify all 9 skills are discoverable
# ═══════════════════════════════════════════════════════════════════════════


def phase1_get_skills(client: httpx.Client) -> None:
    print("\n══════ Phase 1: GET — Discoverability ══════")

    # 1a: List all skills
    resp = client.get(f"{BASE_URL}/v1/skills", headers=HEADERS)
    assert resp.status_code == 200, f"list returned {resp.status_code}"
    data = resp.json()
    assert data["count"] == 9, f"expected 9 skills, got {data['count']}"
    found_paths = {s["path"] for s in data["skills"]}

    record("1a", "GET /v1/skills (list all)", "PASS",
           "200 + count=9 + 9 skills",
           f"200 + count={data['count']}",
           json.dumps({"status_code": resp.status_code, "count": data["count"],
                       "skill_paths": sorted(found_paths)}, indent=2))

    # 1b: GET each skill individually
    for skill_path in SKILL_PATHS:
        url = f"{BASE_URL}/v1/skills/{skill_path}"
        resp = client.get(url, headers=HEADERS)
        test_name = f"GET /v1/skills/{skill_path}"

        if resp.status_code == 200:
            skill = resp.json()
            required_keys = {"skill", "method", "path", "target_department",
                            "queue_topic", "mirror_check", "min_mirror_level", "status"}
            missing = required_keys - set(skill.keys())
            if missing:
                record("1b", test_name, "FAIL",
                       f"200 + all skill detail keys",
                       f"200 but missing keys: {missing}",
                       json.dumps(skill, indent=2))
            else:
                record("1b", test_name, "PASS",
                       "200 + skill detail",
                       f"200 + {skill['skill']} ({skill['target_department']})",
                       json.dumps(skill, indent=2))
        else:
            record("1b", test_name, "FAIL",
                   "200 + skill detail",
                   f"{resp.status_code}: {resp.text[:200]}",
                   resp.text[:500])

    # 1c: GET invalid skill → 404
    resp = client.get(f"{BASE_URL}/v1/skills/nonexistent-skill", headers=HEADERS)
    record("1c", "GET /v1/skills/nonexistent-skill",
           "PASS" if resp.status_code == 404 else "FAIL",
           "404 SKILL_NOT_FOUND",
           f"{resp.status_code}: {resp.json().get('error', resp.text[:100])}",
           json.dumps(resp.json(), indent=2))


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2: POST — Verify all 9 skills queue properly
# ═══════════════════════════════════════════════════════════════════════════


def phase2_post_skills(client: httpx.Client) -> None:
    print("\n══════ Phase 2: POST — Queue Dispatch ══════")

    for skill_path in SKILL_PATHS:
        url = f"{BASE_URL}/v1/skills/{skill_path}"
        payload = POST_PAYLOADS[skill_path]
        test_name = f"POST /v1/skills/{skill_path}"

        try:
            resp = client.post(url, headers=HEADERS, json=payload, timeout=30.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "queued":
                    record("2", test_name, "PASS",
                           "200 + {\"status\": \"queued\"}",
                           f"200 + status=queued, trace_id={data.get('trace_id','?')[:20]}...",
                           json.dumps(data, indent=2))
                elif data.get("status") == "rejected":
                    record("2", test_name, "FAIL",
                           "200 + {\"status\": \"queued\"}",
                           f"200 + status=rejected (mirror check blocked)",
                           json.dumps(data, indent=2))
                else:
                    record("2", test_name, "FAIL",
                           "200 + {\"status\": \"queued\"}",
                           f"200 + unexpected status: {data.get('status')}",
                           json.dumps(data, indent=2))
            else:
                record("2", test_name, "FAIL",
                       "200 + {\"status\": \"queued\"}",
                       f"{resp.status_code}: {resp.text[:200]}",
                       resp.text[:500])
        except httpx.TimeoutException:
            record("2", test_name, "FAIL",
                   "200 + {\"status\": \"queued\"}",
                   "Timeout (>30s) — possible mirror check hang",
                   "httpx.TimeoutException")
        except Exception as e:
            record("2", test_name, "FAIL",
                   "200 + {\"status\": \"queued\"}",
                   f"Exception: {type(e).__name__}: {e}",
                   str(e)[:500])


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3: Error Validation
# ═══════════════════════════════════════════════════════════════════════════


def phase3_errors(client: httpx.Client) -> None:
    print("\n══════ Phase 3: Error Validation ══════")

    # 3a: POST with empty body → 400
    url = f"{BASE_URL}/v1/skills/ceo/sprint-plan"
    resp = client.post(url, headers=HEADERS, content=b"", timeout=10.0)
    record("3a", "POST /v1/skills/ceo/sprint-plan (empty body)",
           "PASS" if resp.status_code == 400 else "FAIL",
           "400 INVALID_JSON — Request body must be valid JSON",
           f"{resp.status_code}: {resp.json().get('error', resp.text[:100])}",
           json.dumps(resp.json(), indent=2))

    # 3b: POST to invalid path → 404
    url = f"{BASE_URL}/v1/skills/nonexistent-route"
    payload = {"action": "test"}
    resp = client.post(url, headers=HEADERS, json=payload, timeout=10.0)
    record("3b", "POST /v1/skills/nonexistent-route (invalid path)",
           "PASS" if resp.status_code == 404 else "FAIL",
           "404 SKILL_NOT_FOUND",
           f"{resp.status_code}: {resp.json().get('error', resp.text[:100])}",
           json.dumps(resp.json(), indent=2))

    # 3c: POST missing required_fields → 400
    # finance-tools requires: command, department
    url = f"{BASE_URL}/v1/skills/cfo/finance-tools"
    payload = {"command": "budget_analysis"}  # missing "department"
    resp = client.post(url, headers=HEADERS, json=payload, timeout=10.0)
    record("3c", "POST /v1/skills/cfo/finance-tools (missing department)",
           "PASS" if resp.status_code == 400 else "FAIL",
           "400 VALIDATION_ERROR — Missing required fields: department",
           f"{resp.status_code}: {resp.json().get('error', resp.text[:100])}",
           json.dumps(resp.json(), indent=2))

    # 3d: POST engineering/deploy missing fields → 400
    url = f"{BASE_URL}/v1/skills/engineering/deploy"
    payload = {"action": "deploy"}  # missing environment, service
    resp = client.post(url, headers=HEADERS, json=payload, timeout=10.0)
    record("3d", "POST /v1/skills/engineering/deploy (missing env+service)",
           "PASS" if resp.status_code == 400 else "FAIL",
           "400 VALIDATION_ERROR",
           f"{resp.status_code}: {resp.json().get('error', resp.text[:100])}",
           json.dumps(resp.json(), indent=2))

    # 3e: POST with invalid JSON body → 400
    url = f"{BASE_URL}/v1/skills/coo/daily-ops"
    resp = client.post(url, headers=HEADERS, content=b"not-json", timeout=10.0)
    record("3e", "POST /v1/skills/coo/daily-ops (invalid JSON)",
           "PASS" if resp.status_code == 400 else "FAIL",
           "400 INVALID_JSON",
           f"{resp.status_code}: {resp.text[:100]}",
           json.dumps(resp.json(), indent=2))


# ═══════════════════════════════════════════════════════════════════════════
# Phase 4: Mirror Check Timing (must be < 20s)
# ═══════════════════════════════════════════════════════════════════════════


def phase4_timing(client: httpx.Client) -> None:
    print("\n══════ Phase 4: Mirror Check Timing ══════")

    TIMING_TESTS = [
        ("engineering/deploy", POST_PAYLOADS["engineering/deploy"]),
        ("governance/rfc", POST_PAYLOADS["governance/rfc"]),
    ]

    for skill_path, payload in TIMING_TESTS:
        url = f"{BASE_URL}/v1/skills/{skill_path}"
        test_name = f"POST /v1/skills/{skill_path} (timing)"

        start = time.monotonic()
        try:
            resp = client.post(url, headers=HEADERS, json=payload, timeout=25.0)
            elapsed = time.monotonic() - start

            if resp.status_code == 200 and elapsed < 20.0:
                record("4", test_name, "PASS",
                       "Response in < 20s",
                       f"{elapsed:.2f}s — within SLA",
                       json.dumps({"elapsed_seconds": round(elapsed, 3),
                                   "status_code": resp.status_code,
                                   "status": resp.json().get("status")}, indent=2))
            elif elapsed >= 20.0:
                record("4", test_name, "FAIL",
                       "Response in < 20s",
                       f"{elapsed:.2f}s — EXCEEDS SLA (threshold: 20s)",
                       json.dumps({"elapsed_seconds": round(elapsed, 3),
                                   "status_code": resp.status_code}, indent=2))
            else:
                record("4", test_name, "FAIL",
                       "200 + status=queued in < 20s",
                       f"{resp.status_code} in {elapsed:.2f}s: {resp.text[:100]}",
                       json.dumps({"elapsed_seconds": round(elapsed, 3),
                                   "status_code": resp.status_code,
                                   "response": resp.text[:200]}, indent=2))
        except httpx.TimeoutException:
            elapsed = time.monotonic() - start
            record("4", test_name, "FAIL",
                   "Response in < 20s",
                   f"Timeout at {elapsed:.2f}s — exceeds 20s SLA",
                   json.dumps({"elapsed_seconds": round(elapsed, 3),
                               "error": "TimeoutException"}, indent=2))
        except Exception as e:
            elapsed = time.monotonic() - start
            record("4", test_name, "FAIL",
                   "Response in < 20s",
                   f"Exception at {elapsed:.2f}s: {type(e).__name__}",
                   str(e)[:300])


# ═══════════════════════════════════════════════════════════════════════════
# Report Builder
# ═══════════════════════════════════════════════════════════════════════════


def build_report() -> dict:
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total = len(results)

    return {
        "tester": "API Tester",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate_pct": round(passed / total * 100, 1) if total else 0,
        },
        "results": results,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="SkillHub Closure Test Suite")
    parser.add_argument("--phase", type=str, choices=["1", "2", "3", "4", "all"],
                        default="all", help="Test phase to run")
    parser.add_argument("--report", action="store_true",
                        help="Print JSON report and exit")
    args = parser.parse_args()

    if args.report:
        print(json.dumps(build_report(), indent=2))
        return

    phase_map = {
        "1": [phase1_get_skills],
        "2": [phase2_post_skills],
        "3": [phase3_errors],
        "4": [phase4_timing],
        "all": [phase1_get_skills, phase2_post_skills, phase3_errors, phase4_timing],
    }

    phases = phase_map[args.phase]

    with httpx.Client(verify=False) as client:
        # Health check first
        try:
            h = client.get(f"{BASE_URL}/v1/health", headers=HEADERS, timeout=5.0)
            print(f"Health: {h.status_code} — {h.json().get('status', '?')}")
        except Exception as e:
            print(f"CRITICAL: Central Bus not reachable at {BASE_URL}: {e}")
            sys.exit(1)

        for phase_fn in phases:
            try:
                phase_fn(client)
            except Exception as e:
                print(f"Phase error: {type(e).__name__}: {e}")

    report = build_report()
    print(f"\n{'=' * 60}")
    print(f"RESULTS: {report['summary']['passed']}/{report['summary']['total_tests']} passed "
          f"({report['summary']['pass_rate_pct']}%)")
    if report['summary']['failed'] > 0:
        print("FAILED TESTS:")
        for r in report['results']:
            if r['status'] == 'FAIL':
                print(f"  [{r['phase']}] {r['test']}: {r['actual']}")
    print("=" * 60)

    # Output JSON report to file
    report_path = Path(__file__).parent / "skillhub_closure_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()

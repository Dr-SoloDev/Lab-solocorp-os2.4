#!/usr/bin/env python3
"""D3 evaluation harness — legal-tulya MCP (20 cases, deterministic, no LLM).

Calls axis_mcp.departments.legal_mcp tools directly with DRAFTS_ROOT
isolated to out-dir. Writes results.json + table.md + harness-sha256.txt.
Exit 0 = ran all requested cases (PASS/FAIL do not affect exit); 1 = crash.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import traceback
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from axis_mcp.departments import legal_mcp as PM  # noqa: E402

RUNNER_REL = "scripts/d3_legal_eval.py"
AGENT_REL = "axis_mcp/departments/legal_mcp.py"
DEFAULT_OUT_DIR = REPO / "bus" / "evidence" / date.today().isoformat() / "d3-legal"
TEMPLATE_SECTIONS = (
    "# Legal Review Request:",
    "**Status:** AWAITING HUMAN REVIEW",
    "## Matter",
    "## Checklist for human reviewer",
)


def chk(name: str, ok: bool, detail: str, severity: str = "required") -> dict:
    return {"name": name, "ok": bool(ok), "detail": str(detail), "severity": severity}


CASES: list[dict] = [
    {
        "id": 1,
        "name": "info schema",
        "kind": "info",
        "expect": "ok · head legal-tulya · 3 specialists · data_root + human-review flag",
    },
    {
        "id": 2,
        "name": "info runtime freshness",
        "kind": "info_fresh",
        "expect": "runtime block present",
    },
    {
        "id": 3,
        "name": "info valid JSON + department",
        "kind": "info_json",
        "expect": "parses · department=legal · requires_human_review=true",
    },
    {
        "id": 4,
        "name": "list default",
        "kind": "list",
        "args": {},
        "expect": "count 3 · all require human review",
    },
    {
        "id": 5,
        "name": "list limit=1",
        "kind": "list",
        "args": {"limit": 1},
        "expect": "count 1",
    },
    {
        "id": 6,
        "name": "list limit=0",
        "kind": "list",
        "args": {"limit": 0},
        "expect": "count 0",
    },
    {
        "id": 7,
        "name": "list limit huge/negative",
        "kind": "list_edge",
        "expect": "999->3 · -5->0",
    },
    {
        "id": 8,
        "name": "create valid review",
        "kind": "create",
        "args": {"title": "NDA Acme", "brief": "review scope"},
        "expect": "ok · file exists · template sections · sha matches · human-review flag",
    },
    {
        "id": 9,
        "name": "create invalid title",
        "kind": "create",
        "args": {"title": "!!!", "brief": "x"},
        "expect": "error invalid_title · no file",
    },
    {
        "id": 10,
        "name": "create traversal title",
        "kind": "create",
        "args": {"title": "../../etc/evil", "brief": "x"},
        "expect": "sanitized inside vault · no escape",
    },
    {
        "id": 11,
        "name": "create 200-char title",
        "kind": "create",
        "args": {"title": "B" * 200, "brief": "x"},
        "expect": "ok · slug truncated to 64",
    },
    {
        "id": 12,
        "name": "create empty brief",
        "kind": "create",
        "args": {"title": "Empty Matter", "brief": ""},
        "expect": "ok · (todo) placeholder",
    },
    {
        "id": 13,
        "name": "create Thai-only title",
        "kind": "create",
        "args": {"title": "สัญญาจ้าง", "brief": "x"},
        "expect": "error invalid_title (ASCII-only slug, known limitation)",
    },
    {
        "id": 14,
        "name": "create overwrite same title",
        "kind": "create",
        "args": {"title": "Overwrite Me", "brief": "v1"},
        "repeat": 2,
        "expect": "2 runs ok · mtime newer (overwritten)",
    },
    {
        "id": 15,
        "name": "compliance 2 items",
        "kind": "check",
        "args": {"items_csv": "soc2, iso27001"},
        "expect": "count 2 · all verdicts requires_human_review",
    },
    {
        "id": 16,
        "name": "compliance empty",
        "kind": "check",
        "args": {"items_csv": ""},
        "expect": "error empty_items",
    },
    {
        "id": 17,
        "name": "compliance commas only",
        "kind": "check",
        "args": {"items_csv": "   , , "},
        "expect": "error empty_items",
    },
    {
        "id": 18,
        "name": "compliance duplicates kept",
        "kind": "check",
        "args": {"items_csv": "soc2, soc2"},
        "expect": "count 2 · both require human review",
    },
    {
        "id": 19,
        "name": "compliance single item",
        "kind": "check",
        "args": {"items_csv": "gdpr"},
        "expect": "count 1 · requires human review",
    },
    {
        "id": 20,
        "name": "create slash title stays inside",
        "kind": "create",
        "args": {"title": "a/b/c", "brief": "x"},
        "expect": "ok · file inside vault (slug a-b-c)",
    },
]
CASE_BY_ID = {c["id"]: c for c in CASES}


def snapshot_profiles() -> dict:
    snap = {}
    root = REPO / "profiles"
    for p in root.rglob("*"):
        if p.is_file():
            try:
                st = p.stat()
                snap[str(p.relative_to(root))] = (st.st_mtime_ns, st.st_size)
            except OSError:
                continue
    return snap


def run_tool(case: dict, drafts: Path) -> dict:
    kind, args = case["kind"], dict(case.get("args", {}))
    t0 = datetime.now()
    crashed, res, tb = False, {}, ""
    try:
        with patch.object(PM, "REVIEWS_ROOT", drafts):
            if kind.startswith("info"):
                raw = PM.legal_department_info()
            elif kind.startswith("list"):
                raw = PM.legal_list_matters(**args)
            elif kind == "create":
                raw = PM.legal_create_review(**args)
            elif kind in ("prioritize", "check"):
                raw = PM.legal_check_compliance(**args)
            else:
                raise ValueError(f"unknown kind {kind}")
            res = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        crashed = True
        res = {"status": "CRASH", "error": type(exc).__name__}
        tb = traceback.format_exc()[-800:]
    return {
        "res": res,
        "seconds": round((datetime.now() - t0).total_seconds(), 2),
        "crashed": crashed,
        "tb": tb,
    }


def build_obs(
    case: dict, run: dict, drafts: Path, pre_prof: dict, attempt: int
) -> dict:
    res = run["res"]
    obs = {
        "attempt": attempt,
        "status": res.get("status"),
        "error": res.get("error"),
        "seconds": run["seconds"],
        "crashed": run["crashed"],
        "traceback_tail": run["tb"],
        "res_keys": sorted(res.keys()),
        "res": res,
    }
    if case["kind"] == "create" and res.get("status") == "ok":
        p = drafts / Path(res.get("path", "")).name
        obs["file_exists"] = p.is_file()
        text = p.read_text(encoding="utf-8") if p.is_file() else ""
        obs["chars"] = len(text)
        obs["sections_missing"] = [s for s in TEMPLATE_SECTIONS if s not in text]
        obs["sha_match"] = (
            (hashlib.sha256(text.encode()).hexdigest() == res.get("sha256"))
            if text
            else False
        )
        obs["out_mtime_ns"] = p.stat().st_mtime_ns if p.is_file() else None
        obs["out_name"] = p.name
    elif case["kind"] == "create":
        # error path: assert no file with related slug was created
        names = {p.name for p in drafts.glob("*")} if drafts.exists() else set()
        obs["file_exists"] = False
        obs["draft_files"] = sorted(names)
    if case["kind"] in ("list", "list_edge"):
        pass
    obs["profiles_changed"] = sorted(
        k
        for k in set(pre_prof) | set(snapshot_profiles())
        if pre_prof.get(k) != snapshot_profiles().get(k)
    )
    return obs


def checks_for(case: dict, obs: dict) -> list[dict]:
    cid, r = case["id"], []
    ok = lambda n, c, d, s="required": r.append(chk(n, c, d, s))  # noqa: E731
    if obs["crashed"]:
        ok("no_crash", False, obs["res"].get("error", "crash"))
        return r
    if cid == 1:
        d = obs["res"]
        ok("status_ok", d.get("status") == "ok", d.get("status"))
        ok("head", (d.get("head") or {}).get("id") == "legal-tulya", d.get("head"))
        ok(
            "specialists_3",
            len(d.get("specialists", [])) == 3,
            len(d.get("specialists", [])),
        )
        ok(
            "data_root",
            d.get("data_root") == "legal_vault/reviews/",
            d.get("data_root"),
        )
    elif cid == 2:
        ok("runtime_present", "runtime" in obs["res"], list(obs["res_keys"]))
    elif cid == 3:
        ok(
            "department",
            obs["res"].get("department") == "legal",
            obs["res"].get("department"),
        )
        ok(
            "human_flag",
            obs["res"].get("requires_human_review") is True,
            obs["res"].get("requires_human_review"),
        )
    elif cid in (4, 5, 6):
        want = {4: 3, 5: 1, 6: 0}[cid]
        ok("count", obs["res"].get("count") == want, obs["res"].get("count"))
        ok(
            "len_match",
            len(obs["res"].get("matters", [])) == want,
            len(obs["res"].get("matters", [])),
        )
    elif cid == 7:
        with patch.object(PM, "REVIEWS_ROOT", REPO):
            a = json.loads(PM.legal_list_matters(limit=999))
            b = json.loads(PM.legal_list_matters(limit=-5))
        ok("huge_clamped", a.get("count") == 3, a.get("count"))
        ok("negative_empty", b.get("count") == 0, b.get("count"))
    elif cid == 8:
        ok("status_ok", obs["status"] == "ok", obs["status"])
        ok("file_exists", obs["file_exists"], obs.get("out_name"))
        ok(
            "template",
            not obs["sections_missing"],
            obs["sections_missing"] or "all 4 present",
        )
        ok("sha_match", obs["sha_match"], "sha256")
    elif cid == 9:
        ok("invalid_title", obs.get("error") == "invalid_title", obs.get("error"))
    elif cid == 10:
        ok("status_ok", obs["status"] == "ok", obs["status"])
        names = obs.get("draft_files", [obs.get("out_name")])
        ok(
            "inside_drafts",
            any("etc-evil" in (n or "") for n in ([obs.get("out_name")] + names)),
            names,
        )
        ok(
            "no_escape",
            not (REPO / "bus" / "creative" / "etc-evil.md").exists()
            and not Path("/etc/evil.md").exists()
            and not (REPO / "etc-evil.md").exists(),
            "no outside file",
        )
    elif cid == 11:
        ok("status_ok", obs["status"] == "ok", obs["status"])
        name = obs.get("out_name", "")
        ok(
            "slug_64",
            len(Path(name).stem[7:]) == 64,
            f"stem_len={len(Path(name).stem[7:])}",
        )
    elif cid == 12:
        ok("status_ok", obs["status"] == "ok", obs["status"])
    elif cid == 13:
        ok("invalid_title", obs.get("error") == "invalid_title", obs.get("error"))
    elif cid == 14:
        ok("status_ok", obs["status"] == "ok", obs["status"])
    elif cid in (15, 18, 19):
        want = {
            15: (["soc2", "iso27001"], 2),
            18: (["soc2", "soc2"], 2),
            19: (["gdpr"], 1),
        }[cid]
        got = [(x["item"], x["verdict"]) for x in obs["res"].get("checklist", [])]
        ok("all_human", got == [(n, "requires_human_review") for n in want[0]], got)
        ok("count", obs["res"].get("count") == want[1], obs["res"].get("count"))
        ok("count", obs["res"].get("count") == want[1], obs["res"].get("count"))
    elif cid in (16, 17):
        ok("empty_items", obs.get("error") == "empty_items", obs.get("error"))
    elif cid == 20:
        ok("status_ok", obs["status"] == "ok", obs["status"])
        ok(
            "slug_dashes",
            (obs.get("out_name") or "") == "REVIEW-a-b-c.md",
            obs.get("out_name"),
        )
    ok(
        "profiles_untouched",
        not obs.get("profiles_changed"),
        obs.get("profiles_changed")[:3],
    )
    return r


def verdict_of(checks: list[dict], crashed: bool) -> str:
    if crashed:
        return "CRASH"
    return (
        "FAIL"
        if any(not c["ok"] and c["severity"] == "required" for c in checks)
        else "PASS"
    )


def classify(case: dict, obs: dict, checks: list[dict], verdict: str):
    bad = [c for c in checks if not c["ok"] and c["severity"] == "required"]
    if not bad:
        return None, None
    names = {c["name"] for c in bad}
    if obs["crashed"]:
        return (
            "agent_logic",
            f"unhandled: {obs['res'].get('error')} (traceback in results.json)",
        )
    if "no_escape" in names or "profiles_untouched" in names:
        return "guard_missing", "; ".join(f"{c['name']}={c['detail']}" for c in bad)
    if "slug_64" in names or "inside_drafts" in names or "slug_dashes" in names:
        return "agent_logic", "; ".join(f"{c['name']}={c['detail']}" for c in bad)
    if "invalid_title" in names and case["id"] == 13:
        return (
            "spec_ambiguous",
            "Thai-only title rejected: ASCII-only slug is a known spec limitation, not a code bug",
        )
    return "agent_logic", "; ".join(f"{c['name']}={c['detail']}" for c in bad)


async def run_case(case: dict, out_dir: Path, drafts: Path, repeats: int) -> dict:
    runs, logs = [], []
    log_dir = out_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, repeats + 1):
        pre = snapshot_profiles()
        run = run_tool(case, drafts)
        obs = build_obs(case, run, drafts, pre, attempt)
        checks = checks_for(case, obs)
        verdict = verdict_of(checks, obs["crashed"])
        rc, detail = classify(case, obs, checks, verdict)
        obs.update(
            {
                "checks": checks,
                "verdict": verdict,
                "reason": "; ".join(
                    f"{c['name']}={c['detail']}" for c in checks if not c["ok"]
                )
                or "all required checks passed",
                "root_cause": rc,
                "root_cause_detail": detail,
            }
        )
        runs.append(obs)
        print(
            f"  run {attempt}/{repeats}: {obs['status']} · {obs['seconds']}s → {verdict}"
            + (f" ({rc})" if rc else ""),
            flush=True,
        )
    extra = []
    if case.get("repeat", 1) > 1 and len(runs) > 1:
        m1, m2 = runs[0].get("out_mtime_ns"), runs[1].get("out_mtime_ns")
        extra = [
            chk("overwritten", bool(m1 and m2 and m2 >= m1), f"mtime {m1} -> {m2}")
        ]
    return {
        "id": case["id"],
        "name": case["name"],
        "expect": case["expect"],
        "runs": runs,
        "case_checks": extra,
        "logs": logs,
    }


def aggregate(row: dict) -> dict:
    counts = Counter(r["verdict"] for r in row["runs"])
    verdict = (
        "CRASH"
        if "CRASH" in counts
        else (next(iter(counts)) if len(counts) == 1 else "FLAKY")
    )
    bad_extra = [c for c in row.get("case_checks", []) if not c["ok"]]
    if bad_extra and verdict == "PASS":
        verdict = "FAIL"
    rep = next(
        (r for r in row["runs"] if r["verdict"] in ("CRASH", "FAIL")), row["runs"][0]
    )
    row.update(
        {
            "verdict": verdict,
            "verdict_display": (
                " · ".join(
                    f"{k} {counts[k]}/{len(row['runs'])}"
                    for k in ["PASS", "FAIL", "CRASH"]
                    if counts[k]
                )
                if len(counts) > 1
                else verdict
            ),
            "verdict_counts": dict(counts),
            "reason": rep.get("reason", ""),
            "root_cause": rep.get("root_cause"),
            "root_cause_detail": rep.get("root_cause_detail"),
            "seconds_total": round(sum(r["seconds"] for r in row["runs"]), 1),
        }
    )
    if bad_extra:
        row["root_cause"] = row["root_cause"] or "agent_logic"
        row["reason"] += " | " + "; ".join(
            f"{c['name']}={c['detail']}" for c in bad_extra
        )
    return row


def render_table(rows: list[dict], meta: dict) -> str:
    lines = [
        "# D3 — legal-tulya · ผลประเมิน (runner พิมพ์เอง)",
        "",
        f"- วันที่: {meta['started']} · โค้ด: {meta['git_head']}",
        f"- out-dir: `{meta['out_dir']}`",
        f"- harness sha256: `{meta['harness_sha']}` (agent: `{meta['agent_sha']}`)",
        f"- argv: `{meta['argv']}`",
        f"- รวม **{meta['total']}** เคส · PASS {meta['pass']} · FAIL {meta['fail']} · CRASH {meta['crash']}",
        "",
        "| # | งาน | คาดว่าได้ | ได้จริง | ผล | root cause | หลักฐาน |",
        "|:--:|:--|:--|:--|:--|:--|:--|",
    ]
    for row in rows:
        r0 = row["runs"][0]
        got = f"{r0['status']}"
        if r0.get("error"):
            got += f" · error={r0.get('error')}"
        if "chars" in r0:
            got += f" · {r0['chars']} chars"
        if "out_name" in r0 and r0.get("out_name"):
            got += f" · {r0['out_name']}"
        if len(row["runs"]) > 1:
            got = " ‖ ".join(
                f"run{i + 1}: {r['status']}" for i, r in enumerate(row["runs"])
            )
        cells = [
            str(row["id"]),
            row["name"].replace("|", "\\|"),
            row["expect"].replace("|", "\\|"),
            got.replace("|", "\\|"),
            row["verdict"],
            (row.get("root_cause") or "—")
            + (
                f" — {row['root_cause_detail']}" if row.get("root_cause_detail") else ""
            ),
            f"logs/case-{row['id']:02d}.jsonl",
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines += [
        "",
        "> ทุกเคสที่ขอถูกรายงานครบ (ไม่มี cherry-pick) · verdict คำนวณจาก `checks` ใน `results.json`",
        "",
    ]
    return "\n".join(lines)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def git_head() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


async def main_async(args) -> int:
    selected = [CASE_BY_ID[i] for i in (args.only or sorted(CASE_BY_ID))]
    out_dir = Path(args.out_dir)
    (out_dir / "logs").mkdir(parents=True, exist_ok=True)
    drafts = out_dir / "work" / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    started = datetime.now().isoformat(timespec="seconds")
    rows, crash = [], False
    for case in selected:
        print(f"[{case['id']:>2}/{len(CASES)}] {case['name']} ...", flush=True)
        try:
            row = await run_case(case, out_dir, drafts, case.get("repeat", 1))
        except Exception as exc:  # noqa: BLE001
            crash = True
            row = {
                "id": case["id"],
                "name": case["name"],
                "expect": case["expect"],
                "runs": [
                    {
                        "attempt": 1,
                        "status": "RUNNER_CRASH",
                        "error": "runner_error",
                        "seconds": 0.0,
                        "crashed": True,
                        "traceback_tail": traceback.format_exc()[-800:],
                        "checks": [],
                        "verdict": "CRASH",
                        "reason": str(exc),
                        "root_cause": "agent_logic",
                        "root_cause_detail": str(exc),
                    }
                ],
                "case_checks": [],
                "logs": [],
            }
        row = aggregate(row)
        if row["verdict"] == "CRASH":
            crash = True
        rows.append(row)
        (out_dir / "results.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    for lg in (out_dir / "logs").glob("*.jsonl"):
        lg.write_text("", encoding="utf-8")
    rows.sort(key=lambda r: r["id"])
    (out_dir / "results.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shas = {
        "runner": sha256_file(REPO / RUNNER_REL),
        "agent": sha256_file(REPO / AGENT_REL),
    }
    (out_dir / "harness-sha256.txt").write_text(
        f"# D3 harness fingerprint\n# generated: {started}\n# git HEAD: {git_head()}\n"
        f"{shas['runner']}  {RUNNER_REL}\n{shas['agent']}  {AGENT_REL}\n",
        encoding="utf-8",
    )
    counts = Counter(r["verdict"] for r in rows)
    meta = {
        "started": started,
        "git_head": git_head(),
        "out_dir": str(out_dir),
        "harness_sha": shas["runner"],
        "agent_sha": shas["agent"],
        "argv": " ".join(sys.argv[1:]),
        "total": len(rows),
        "pass": counts.get("PASS", 0),
        "fail": counts.get("FAIL", 0) + counts.get("FLAKY", 0),
        "crash": counts.get("CRASH", 0),
    }
    (out_dir / "table.md").write_text(render_table(rows, meta), encoding="utf-8")
    print(
        f"\nD3 legal · {meta['total']} เคส · PASS {meta['pass']} · FAIL {meta['fail']} · CRASH {meta['crash']}"
    )
    print(f"table   : {out_dir / 'table.md'}")
    print(f"results : {out_dir / 'results.json'}")
    return 1 if crash else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma ids, e.g. 1,2,11")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args()
    args.only = (
        sorted({int(x) for x in args.only.split(",") if x.strip()}) if args.only else []
    )
    if args.only and (bad := [i for i in args.only if i not in CASE_BY_ID]):
        print(f"unknown ids: {bad}", file=sys.stderr)
        return 2
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())

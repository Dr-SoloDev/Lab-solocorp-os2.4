#!/usr/bin/env python3
"""D2 independent verifier — team-content-media-editor.

Checker != maker: does not trust agent self-report. Reads files from disk
and checks 6 gates per docs/certification/D1-media-editor.md section 5.

Usage:
    python scripts/verify_d2_media_editor.py --render <path> [--out <path>] [--json <path>]

Exit codes: 0 = all 6 pass, 1 = fail, 2 = agent crashed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SOURCES = (
    "profiles/15-content-creator/sek/team/02-content-media-editor.SOUL.md",
    "axis_mcp/departments/content_skills/media-production/SKILL.md",
)
SECTIONS = ("SHA-256", "## Specs", "## LUFS", "## Gate Decision")
QA_ROOT = REPO / "bus" / "creative" / "media-qa"
SCAN_ROOTS = (
    "bus",
    "scripts",
    "workers",
    "profiles",
    "docs",
    "decisions",
    "rules",
    "sop",
)
SKIP_PARTS = {
    ".git",
    ".jj",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".codegraph",
}


def _snapshot() -> set[str]:
    out = set()
    for root in SCAN_ROOTS:
        base = REPO / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and not any(part in SKIP_PARTS for part in p.parts):
                out.add(str(p))
    return out


def _read_log(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    rows = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({"tool": "CORRUPT", "raw": line})
    return rows


async def _run_agent(render: Path, out: Path | None, log: Path) -> dict:
    from workers.agents.media_editor_agent import MediaEditorAgent

    agent = MediaEditorAgent(log_path=str(log))
    params: dict = {"render_path": str(render)}
    if out:
        params["out_path"] = str(out)
    return await agent.execute({"payload": {"params": params}})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument(
        "--log",
        default="bus/evidence/2026-11-23/d2-media-editor/tool-calls-verify.jsonl",
    )
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    render = Path(args.render)
    log = REPO / args.log
    log.unlink(missing_ok=True)

    before = _snapshot()
    try:
        result = asyncio.run(
            _run_agent(render, Path(args.out) if args.out else None, log)
        )
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED agent crashed: {exc}")
        return 2

    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    calls = _read_log(log)
    read_paths = [str(c.get("args")) for c in calls if c.get("tool") == "read_file"]

    missing_src = [s for s in SOURCES if s not in read_paths]
    check(
        "1 read SOUL+SKILL",
        not missing_src,
        f"read {len(read_paths)} files"
        + (f" MISSING {missing_src}" if missing_src else ""),
    )

    check(
        "2 read render record",
        any(str(render) in p for p in read_paths),
        f"render={render}",
    )

    raw_out = str((result.get("details") or {}).get("out_path", "") or "")
    out_path = Path(raw_out) if raw_out else None
    text = ""
    out_err = ""
    if out_path is None:
        out_err = "no out_path in agent result"
    elif not out_path.is_file():
        out_err = f"not a file (exists={out_path.exists()})"
    else:
        try:
            text = out_path.read_text(encoding="utf-8")
        except OSError as exc:
            out_err = f"unreadable: {exc}"
    check(
        "3 write QA checklist",
        not out_err,
        str(out_path) if not out_err else f"{raw_out or '(none)'} — {out_err}",
    )

    missing_sec = [s for s in SECTIONS if s not in text]
    detail4 = f"missing={missing_sec or 'none'}"
    if out_err:
        detail4 = f"unverifiable — {out_err}"
    check("4 checklist has 4 sections", not missing_sec, detail4)

    gate_ok = False
    gate_detail = ""
    if out_err:
        gate_detail = f"unverifiable — {out_err}"
    else:
        try:
            rec = json.loads(Path(render).read_text(encoding="utf-8"))
            rec_gate = rec.get("gate_passed") is False and rec.get("published") is False
            txt_gate = "gate_passed: false" in text and "published: false" in text
            no_approval = "NOT recorded" in text
            gate_ok = rec_gate and txt_gate and no_approval
            gate_detail = (
                f"record_gate={rec_gate} text_gate={txt_gate} no_approval={no_approval}"
            )
        except (OSError, ValueError) as exc:
            gate_detail = f"render unreadable: {exc}"
    check("5 gate integrity untouched", gate_ok, gate_detail)

    after = _snapshot()
    allowed = [
        f
        for f in (after - before)
        if Path(f).is_relative_to(QA_ROOT) or Path(f).is_relative_to(log.parent)
    ]
    leaked = sorted(after - before - set(allowed))
    check("6 no write outside scope", not leaked, f"leaked={leaked or 'none'}")

    passed = all(c["ok"] for c in checks)
    payload = {
        "agent_result": result,
        "checks": checks,
        "passed": passed,
        "tool_call_count": len(calls),
        "render": str(render),
    }
    if args.json:
        Path(args.json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"\n{'=' * 68}")
    for c in checks:
        print(f"{'PASS' if c['ok'] else 'FAIL'} {c['check']:<32} {c['detail']}")
    print(f"{'=' * 68}")
    print(f"agent status = {result.get('status')} tool calls = {len(calls)}")
    print(f"D2 VERDICT: {'PASSED' if passed else 'RETURNED'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""mcp-diagnose — จัดกลุ่ม process ของ axis_mcp ตาม (ppid, cwd)

ทำไมต้องมี (Wave 3 · Runtime Visibility · 2026-11-23)
────────────────────────────────────────────────────
การนับ MCP ด้วย `pgrep -af axis_mcp` ให้ตัวเลขที่เชื่อถือไม่ได้ เพราะ
  1. `pgrep` นับ shell/คำสั่งของตัวเองเข้าไปด้วย (เคยรายงาน "11 ตัว" ทั้งที่จริง 9)
  2. ไม่แยก project root → MCP ของ worktree กับ canonical ปนกันในกองเดียว
  3. ไม่รู้ว่า ppid ไหนเป็น client instance ไหน

ตัวนับที่ถูกต้องจึงต้อง:
  · อ่าน /proc โดยตรง (ไม่ parse `ps`, ไม่นับตัวเอง)
  · จัดกลุ่มตาม (ppid, cwd) — 1 กลุ่ม = MCP ชุดของ client instance หนึ่งตัว
  · flag "duplicate" เฉพาะเมื่อ module เดียวกันซ้ำ **ภายใน cwd เดียวกัน**
    (module เดียวกันแต่คนละ project root = คนละ deployment ไม่ใช่ duplicate)

ใช้
───
  python scripts/mcp-diagnose.py            # อ่านคน
  python scripts/mcp-diagnose.py --json     # machine-readable
  python scripts/mcp-diagnose.py --strict   # exit 1 ถ้าเจอ duplicate จริง (สำหรับ CI)

Exit code: 0 = สำเร็จ (แม้เจอ duplicate) · 1 = --strict และเจอ duplicate · 2 = อ่าน /proc ไม่ได้
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

PROC = Path("/proc")
MATCH = "axis_mcp"


# ── /proc readers ───────────────────────────────────────────────────────
def _read_cmdline(pid: int) -> list[str]:
    try:
        raw = (PROC / str(pid) / "cmdline").read_bytes()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return []
    return [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]


def _read_stat(pid: int) -> dict | None:
    """อ่าน /proc/<pid>/stat — comm อาจมีช่องว่าง/วงเล็บ → split หลัง ')' ตัวสุดท้าย"""
    try:
        raw = (PROC / str(pid) / "stat").read_text()
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return None
    rparen = raw.rfind(")")
    if rparen < 0:
        return None
    fields = raw[rparen + 2 :].split()
    # หลัง comm: index 0 = state (field 3) → ppid = field 4 = index 1
    try:
        return {"ppid": int(fields[1]), "start_ticks": int(fields[19])}
    except (IndexError, ValueError):
        return None


def _read_cwd(pid: int) -> str:
    try:
        return os.readlink(f"/proc/{pid}/cwd")
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return "(unavailable)"


def _boot_time() -> float | None:
    """btime จาก /proc/stat (epoch วินาที) — ใช้แปลง starttime ticks เป็นเวลาจริง"""
    try:
        for line in (PROC / "stat").read_text().splitlines():
            if line.startswith("btime "):
                return float(line.split()[1])
    except OSError:
        pass
    return None


def _clock_ticks() -> int:
    try:
        return os.sysconf("SC_CLK_TCK")
    except (ValueError, OSError):
        return 100


def _module_of(argv: list[str]) -> str | None:
    """ดึงชื่อ module ที่รัน — รองรับทั้ง `-m axis_mcp.x` และ `python axis_mcp/server.py`"""
    for i, arg in enumerate(argv):
        if arg in ("-m", "--module") and i + 1 < len(argv):
            candidate = argv[i + 1]
            if MATCH in candidate:
                return candidate
        if arg.endswith(".py") and MATCH in arg:
            # แสดงเป็น dotted path ให้เทียบกันได้: axis_mcp/server.py → axis_mcp.server
            rel = arg[arg.index(MATCH) :]
            return rel.removesuffix(".py").replace("/", ".")
    # fallback: argument ไหนก็ตามที่มี axis_mcp แล้วไม่ใช่ path ของ interpreter
    for arg in argv:
        if MATCH in arg and not arg.startswith("-") and "/python" not in arg:
            return arg
    return None


def _scan() -> tuple[list[dict], str | None]:
    """คืน (processes, error) — self-excluded เสมอ"""
    if not PROC.exists():  # pragma: no cover — Linux only
        return [], "ไม่พบ /proc — ตัวตรวจนี้รองรับ Linux เท่านั้น"

    boot = _boot_time()
    hz = _clock_ticks()
    self_pid = os.getpid()
    out: list[dict] = []

    for entry in PROC.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == self_pid:
            continue  # ห้ามนับตัวเอง (เหตุผลที่ pgrep ให้ตัวเลขเกิน)
        argv = _read_cmdline(pid)
        if not argv:
            continue
        text = " ".join(argv)
        if MATCH not in text:
            continue
        module = _module_of(argv)
        if not module:
            continue
        stat = _read_stat(pid)
        ppid = stat["ppid"] if stat else -1
        start = None
        if boot is not None and stat is not None:
            start = (
                datetime.fromtimestamp(boot + stat["start_ticks"] / hz, tz=timezone.utc)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S")
            )
        out.append(
            {
                "pid": pid,
                "ppid": ppid,
                "start": start,
                "module": module,
                "cwd": _read_cwd(pid),
                "executable": argv[0] if argv else None,
            }
        )

    out.sort(key=lambda p: (p["ppid"], p["cwd"], p["module"], p["pid"]))
    return out, None


# ── grouping ────────────────────────────────────────────────────────────
def build_report(processes: list[dict], error: str | None = None) -> dict:
    groups: dict[tuple[int, str], list[dict]] = {}
    for proc in processes:
        groups.setdefault((proc["ppid"], proc["cwd"]), []).append(proc)

    group_list = []
    duplicates: list[dict] = []
    for (ppid, cwd), procs in sorted(
        groups.items(), key=lambda kv: (kv[0][1], kv[0][0])
    ):
        by_module: dict[str, list[int]] = {}
        for proc in procs:
            by_module.setdefault(proc["module"], []).append(proc["pid"])
        dup_here = [
            {"module": module, "pids": pids, "cwd": cwd, "ppid": ppid}
            for module, pids in sorted(by_module.items())
            if len(pids) > 1
        ]
        duplicates.extend(dup_here)
        group_list.append(
            {
                "ppid": ppid,
                "cwd": cwd,
                "count": len(procs),
                "processes": procs,
                "duplicates": dup_here,
            }
        )

    # module เดียวกันแต่คนละ project root — ข้อมูลประกอบ ไม่ใช่ duplicate
    roots_by_module: dict[str, set[str]] = {}
    for proc in processes:
        roots_by_module.setdefault(proc["module"], set()).add(proc["cwd"])
    cross_root = sorted(m for m, roots in roots_by_module.items() if len(roots) > 1)

    return {
        "generated_at": datetime.now(timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "match": MATCH,
        "total_processes": len(processes),
        "group_count": len(group_list),
        "duplicate_count": len(duplicates),
        "duplicates": duplicates,
        "cross_root_modules": cross_root,
        "groups": group_list,
        "verdict": "DUPLICATE" if duplicates else "OK",
        "error": error,
    }


def format_human(report: dict) -> str:
    lines: list[str] = []
    lines.append(
        f"axis_mcp process diagnosis — {report['generated_at']} ({report['host']})"
    )
    if report.get("error"):
        lines.append(f"ERROR: {report['error']}")
        return "\n".join(lines)
    lines.append(
        f"Total processes: {report['total_processes']} · "
        f"Groups (ppid, cwd): {report['group_count']} · "
        f"Duplicates: {report['duplicate_count']}"
    )
    if not report["groups"]:
        lines.append("")
        lines.append("ไม่พบ process axis_mcp ที่รันอยู่")
        return "\n".join(lines)

    for index, group in enumerate(report["groups"], start=1):
        lines.append("")
        lines.append(
            f"Group {index} — ppid {group['ppid']} · cwd {group['cwd']} "
            f"({group['count']} processes)"
        )
        lines.append(f"  {'PID':>7}  {'PPID':>7}  {'START':<19}  MODULE")
        for proc in group["processes"]:
            start = proc["start"] or "-"
            lines.append(
                f"  {proc['pid']:>7}  {proc['ppid']:>7}  {start:<19}  {proc['module']}"
            )

    lines.append("")
    if report["duplicates"]:
        lines.append(
            f"Duplicates (module เดียวกัน ซ้ำใน cwd เดียวกัน): {report['duplicate_count']}"
        )
        for dup in report["duplicates"]:
            lines.append(
                f"  ✗ {dup['module']} × {len(dup['pids'])} ใน {dup['cwd']} "
                f"(pids {dup['pids']}) — ควรมีตัวเดียว"
            )
    else:
        lines.append("Duplicates (module เดียวกัน ซ้ำใน cwd เดียวกัน): 0")
    if report["cross_root_modules"]:
        lines.append(
            "Same module across project roots (ไม่ใช่ duplicate): "
            + ", ".join(report["cross_root_modules"])
        )
    lines.append(
        f"RESULT: {report['verdict']} — {report['total_processes']} processes = "
        f"{report['group_count']} groups, {report['duplicate_count']} duplicates"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="จัดกลุ่ม axis_mcp process ตาม (ppid, cwd) และ flag duplicate จริง"
    )
    parser.add_argument("--json", action="store_true", help="พิมพ์ผลเป็น JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 เมื่อเจอ duplicate (module เดียวกันซ้ำใน cwd เดียวกัน)",
    )
    args = parser.parse_args(argv)

    processes, error = _scan()
    report = build_report(processes, error)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_human(report))

    if error:
        return 2
    if args.strict and report["duplicate_count"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

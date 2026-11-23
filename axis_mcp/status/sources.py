"""Read-only probes for the seven AXIS status sources.

Every probe returns the same small dict::

    {"status": "ok|degraded|down|unknown", "fresh": bool,
     "detail": {...}, "warning": str | None}

A probe never raises: each one catches its own failures so the aggregator can
always return partial results. Nothing here writes a file, opens a database
for writing, or sends a POST. Latency is measured by the aggregator so all
sources are timed the same way.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "axis_mcp"

BUSD_URL = "http://127.0.0.1:8099/v1/health"
BROWSE_ENDPOINT = "http://127.0.0.1:19988"
BROWSE_HOST = "127.0.0.1"
BROWSE_PORT = 19988

HTTP_TIMEOUT_SECONDS = 0.9
CLI_TIMEOUT_SECONDS = 0.9
SQLITE_TIMEOUT_SECONDS = 0.3

# Same tolerance as ``axis_mcp/runtime_freshness.py``: filesystem timestamps
# are coarse, so edits within one second of process start do not count.
STARTUP_TOLERANCE_SECONDS = 1.0

STATUS_VALUES = ("ok", "degraded", "down", "unknown")

PROBE_METHODS = {
    "busd": "GET http://127.0.0.1:8099/v1/health (X-API-Key header when set)",
    "cto": "process scan /proc + sqlite3 mode=ro central_bus/cto.db",
    "content": "process scan /proc + read central_bus/content/ + derived restart_required",
    "mcp_freshness": "/proc/<pid>/stat start vs newest axis_mcp/**/*.py mtime",
    "git": "git rev-parse / branch --show-current / status --porcelain",
    "browse": "browse status --json (fallback: TCP 127.0.0.1:19988)",
    "codegraph": "read .codegraph/codegraph.db mode=ro",
}


def _result(
    status: str,
    fresh: bool,
    detail: dict[str, Any] | None = None,
    warning: str | None = None,
) -> dict[str, Any]:
    if status not in STATUS_VALUES:
        raise ValueError(f"invalid status {status!r}")
    return {
        "status": status,
        "fresh": bool(fresh),
        "detail": dict(detail or {}),
        "warning": warning,
    }


def _iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def _boot_time() -> float:
    with open("/proc/stat", encoding="ascii") as handle:
        for line in handle:
            if line.startswith("btime"):
                return float(line.split()[1])
    raise OSError("btime missing from /proc/stat")


def _proc_start_epoch(pid: int) -> float | None:
    """Return a process start time, preferring /proc/<pid>/stat field 22.

    The directory mtime of ``/proc/<pid>`` is the fallback: it is what
    ``runtime_freshness.py`` reads for ``/proc/self``, but it moves when files
    are added to the directory, so field 22 is the accurate source.
    """

    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
        fields = raw.rsplit(")", 1)[1].split()
        ticks = os.sysconf("SC_CLK_TCK")
        return _boot_time() + int(fields[19]) / ticks
    except (OSError, ValueError, IndexError):
        try:
            return Path(f"/proc/{pid}").stat().st_mtime
        except OSError:
            return None


def _mcp_processes() -> list[dict[str, Any]]:
    """List running ``python -m axis_mcp.*`` processes (never this one)."""

    found: list[dict[str, Any]] = []
    self_pid = os.getpid()
    try:
        entries = list(Path("/proc").iterdir())
    except OSError:
        return found

    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == self_pid:
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if not raw:
            continue
        args = [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]
        if "-m" not in args:
            continue
        index = args.index("-m")
        if index + 1 >= len(args):
            continue
        module = args[index + 1]
        if not module.startswith("axis_mcp."):
            continue
        found.append(
            {
                "pid": pid,
                "module": module,
                "started_at": _proc_start_epoch(pid),
            }
        )
    found.sort(key=lambda item: (item["started_at"] or 0.0, item["pid"]))
    return found


def _newest_source() -> tuple[float | None, str | None]:
    newest: tuple[float | None, str | None] = (None, None)
    for path in PACKAGE_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if newest[0] is None or mtime > newest[0]:
            try:
                name = path.relative_to(PROJECT_ROOT).as_posix()
            except ValueError:
                name = path.name
            newest = (mtime, name)
    return newest


def is_fresh(process_started: float | None, newest_mtime: float | None) -> bool:
    """Fresh unless a source is newer than the process start plus tolerance.

    Mirrors ``runtime_freshness.freshness()``: a source makes the process stale
    only when ``mtime > process_started + STARTUP_TOLERANCE_SECONDS``.
    """

    if process_started is None or newest_mtime is None:
        return False
    return newest_mtime <= process_started + STARTUP_TOLERANCE_SECONDS


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def probe_busd() -> dict[str, Any]:
    key = (os.environ.get("SOLOCORP_API_KEY") or "").strip()
    headers = {"X-API-Key": key} if key else {}
    request = urllib.request.Request(BUSD_URL, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            body = response.read(65_536)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            warning = (
                "SOLOCORP_API_KEY missing — set it to read busd health"
                if not key
                else f"busd rejected the API key (HTTP {exc.code})"
            )
            return _result("down", False, {"http_status": exc.code}, warning)
        return _result(
            "down",
            False,
            {"http_status": exc.code},
            f"busd health returned HTTP {exc.code}",
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return _result(
            "down",
            False,
            {"error": type(exc).__name__},
            "busd unreachable at 127.0.0.1:8099 — start the daemon or check the port",
        )

    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return _result(
            "down",
            False,
            {"body_bytes": len(body)},
            "busd health returned non-JSON output — measurement failed",
        )
    if not isinstance(data, dict):
        return _result("down", False, {}, "busd health returned an unexpected payload")

    db = data.get("db") if isinstance(data.get("db"), dict) else {}
    detail = {
        "status": data.get("status"),
        "queue_pending": db.get("queue_pending"),
        "queue_failed": db.get("queue_failed"),
        "queue_dead": db.get("queue_dead"),
        "rules_in_sync": data.get("rules_in_sync"),
        "uptime_seconds": data.get("uptime_seconds"),
        "version": data.get("version"),
    }

    warnings: list[str] = []
    if "status" not in data and "db" not in data:
        return _result(
            "down", False, detail, "busd health payload is missing status and db"
        )
    if not db:
        warnings.append("busd health payload has no db block")
    if data.get("status") != "ok":
        warnings.append(f"busd reports status {data.get('status')!r}")
    if data.get("rules_in_sync") is False:
        warnings.append("busd routing rules are out of sync with routing.json")
    if int(db.get("queue_dead") or 0) > 0:
        warnings.append(f"{db.get('queue_dead')} dead queue item(s) need triage")
    if int(db.get("queue_failed") or 0) > 0:
        warnings.append(f"{db.get('queue_failed')} failed queue item(s) awaiting retry")

    return _result(
        "degraded" if warnings else "ok", True, detail, "; ".join(warnings) or None
    )


def probe_cto() -> dict[str, Any]:
    processes = [p for p in _mcp_processes() if p["module"] == "axis_mcp.cto.server"]
    db_path = PROJECT_ROOT / "central_bus" / "cto.db"
    detail: dict[str, Any] = {
        "process_running": bool(processes),
        "process_count": len(processes),
        "db": "central_bus/cto.db",
    }
    if not db_path.is_file():
        return _result(
            "down",
            False,
            detail,
            "CTO database central_bus/cto.db is missing — cannot measure CTO",
        )

    try:
        connection = sqlite3.connect(
            f"file:{db_path}?mode=ro", uri=True, timeout=SQLITE_TIMEOUT_SECONDS
        )
        try:
            integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
            tables: dict[str, int | None] = {}
            for table in ("tool_calls", "build_artifacts", "qa_evidence"):
                try:
                    tables[table] = connection.execute(
                        f"SELECT COUNT(*) FROM {table}"
                    ).fetchone()[0]
                except sqlite3.Error:
                    tables[table] = None
        finally:
            connection.close()
    except sqlite3.Error as exc:
        return _result(
            "down",
            False,
            {**detail, "error": type(exc).__name__},
            "CTO database could not be read read-only — measurement failed",
        )

    detail.update({"integrity": integrity, "tables": tables})
    missing = sorted(table for table, count in tables.items() if count is None)
    if missing:
        return _result(
            "down",
            False,
            {**detail, "missing_tables": missing},
            "CTO database is missing required table(s): "
            f"{', '.join(missing)} — measurement failed",
        )
    if integrity != "ok":
        return _result(
            "degraded",
            True,
            detail,
            f"CTO database integrity check returned {integrity!r}",
        )
    if not processes:
        return _result(
            "degraded",
            True,
            detail,
            "CTO MCP process is not running; database is readable (on-demand server)",
        )
    return _result("ok", True, detail, None)


def probe_content() -> dict[str, Any]:
    processes = [
        p for p in _mcp_processes() if p["module"] == "axis_mcp.departments.content_mcp"
    ]
    newest_mtime, newest_name = _newest_source()
    content_dir = PROJECT_ROOT / "central_bus" / "content"

    artifacts = 0
    newest_artifact: str | None = None
    newest_artifact_mtime: float | None = None
    scan_error: str | None = None
    if not content_dir.is_dir():
        scan_error = "central_bus/content is missing"
    else:
        try:
            for path in content_dir.rglob("*"):
                if not path.is_file():
                    continue
                artifacts += 1
                try:
                    mtime = path.stat().st_mtime
                except OSError:
                    continue
                if newest_artifact_mtime is None or mtime > newest_artifact_mtime:
                    newest_artifact_mtime = mtime
                    newest_artifact = path.name
        except OSError as exc:
            scan_error = (
                f"central_bus/content could not be listed ({type(exc).__name__})"
            )

    restart_required: bool | None = None
    if processes:
        restart_required = not all(
            is_fresh(process["started_at"], newest_mtime) for process in processes
        )

    detail: dict[str, Any] = {
        "process_running": bool(processes),
        "process_count": len(processes),
        "content_dir": "central_bus/content",
        "artifact_count": artifacts,
        "newest_artifact": newest_artifact,
        "newest_artifact_age_hours": (
            round((time.time() - newest_artifact_mtime) / 3600, 1)
            if newest_artifact_mtime is not None
            else None
        ),
        "restart_required": restart_required,
        "newest_source": newest_name,
        "freshness_method": (
            "stale iff newest axis_mcp/**/*.py mtime > process start + 1s "
            "(same predicate as runtime_freshness)"
        ),
    }

    if scan_error:
        detail["error"] = scan_error
        return _result("down", False, detail, f"{scan_error} — measurement failed")
    if restart_required is None:
        return _result(
            "down",
            False,
            detail,
            "content MCP process is not running — restart_required cannot be "
            "read; start it from the client to verify",
        )
    if restart_required:
        return _result(
            "degraded",
            False,
            detail,
            "content MCP process is older than the newest axis_mcp source — "
            "restart before trusting its answers",
        )
    if artifacts == 0:
        return _result(
            "degraded",
            True,
            detail,
            "content MCP is running but central_bus/content has no artifacts",
        )
    return _result("ok", True, detail, None)


def probe_mcp_freshness() -> dict[str, Any]:
    newest_mtime, newest_name = _newest_source()
    rows = []
    for process in _mcp_processes():
        rows.append(
            {
                "pid": process["pid"],
                "module": process["module"],
                "started_at": _iso(process["started_at"]),
                "fresh": is_fresh(process["started_at"], newest_mtime),
            }
        )
    stale = [row for row in rows if not row["fresh"]]
    detail = {
        "generations": len(rows),
        "stale_count": len(stale),
        "newest_source": newest_name,
        "newest_source_at": _iso(newest_mtime),
        "processes": rows,
    }

    if not rows:
        return _result("down", False, detail, "no axis_mcp MCP process is running")
    if stale:
        names = ", ".join(sorted({row["module"] for row in stale}))
        return _result(
            "degraded",
            False,
            detail,
            f"{len(stale)} MCP process(es) older than {newest_name} — "
            f"restart before trusting results ({names})",
        )
    return _result("ok", True, detail, None)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), *args],
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT_SECONDS,
        check=False,
    )


def probe_git() -> dict[str, Any]:
    try:
        head = _git("rev-parse", "--short", "HEAD")
        if head.returncode != 0:
            return _result(
                "down",
                False,
                {"returncode": head.returncode},
                "git rev-parse failed — is this a git work tree?",
            )
        branch = _git("branch", "--show-current")
        porcelain = _git("--no-optional-locks", "status", "--porcelain")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _result("down", False, {}, f"git probe failed ({type(exc).__name__})")

    if branch.returncode != 0:
        return _result(
            "down",
            False,
            {"returncode": branch.returncode},
            "git branch --show-current failed — measurement failed",
        )
    if porcelain.returncode != 0:
        return _result(
            "down",
            False,
            {"returncode": porcelain.returncode},
            "git status failed — measurement failed",
        )

    branch_name = branch.stdout.strip()
    dirty = [line for line in porcelain.stdout.splitlines() if line.strip()]
    detail = {
        "head": head.stdout.strip(),
        "branch": branch_name or None,
        "dirty_count": len(dirty),
        "detached": not branch_name,
    }
    if not branch_name:
        return _result(
            "degraded", True, detail, "git HEAD is detached — branch context is missing"
        )
    return _result("ok", True, detail, None)


def _browse_paired(data: dict[str, Any]) -> bool | None:
    for key in ("extension", "browsers", "paired"):
        value = data.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, list):
            return bool(value)
        if isinstance(value, dict):
            for inner in ("paired", "connected", "running", "count"):
                candidate = value.get(inner)
                if isinstance(candidate, bool):
                    return candidate
                if isinstance(candidate, int):
                    return candidate > 0
    return None


def probe_browse() -> dict[str, Any]:
    executable = shutil.which("browse")
    detail: dict[str, Any] = {
        "relay_endpoint": BROWSE_ENDPOINT,
        "cli": executable,
    }

    if executable:
        try:
            completed = subprocess.run(
                [executable, "status", "--json"],
                capture_output=True,
                text=True,
                timeout=CLI_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            detail["cli_error"] = type(exc).__name__
            completed = None
        if (
            completed is not None
            and completed.returncode == 0
            and completed.stdout.strip()
        ):
            try:
                data = json.loads(completed.stdout)
            except ValueError:
                data = None
            if isinstance(data, dict):
                relay = data.get("relay") if isinstance(data.get("relay"), dict) else {}
                setup = data.get("setup") if isinstance(data.get("setup"), dict) else {}
                running = bool(relay.get("running"))
                endpoint = relay.get("endpoint") or BROWSE_ENDPOINT
                paired = _browse_paired(data)
                detail.update(
                    {
                        "relay_running": running,
                        "endpoint": endpoint,
                        "version": setup.get("version"),
                        "extension_paired": paired,
                    }
                )
                if not running:
                    return _result(
                        "down",
                        False,
                        detail,
                        f"browse relay is not running at {endpoint} "
                        "(it starts when an agent uses browse)",
                    )
                if paired is True:
                    return _result("ok", True, detail, None)
                if paired is False:
                    return _result(
                        "degraded",
                        True,
                        detail,
                        "browse relay is up but no browser extension is paired",
                    )
                return _result(
                    "degraded",
                    True,
                    detail,
                    "browse relay is up but extension pairing could not be verified",
                )

    if _port_open(BROWSE_HOST, BROWSE_PORT):
        return _result(
            "degraded",
            True,
            detail,
            "browse relay answers but the browse CLI is unavailable; "
            "extension pairing is unknown",
        )
    return _result(
        "down",
        False,
        detail,
        f"browse relay is not running at {BROWSE_ENDPOINT}",
    )


def probe_codegraph() -> dict[str, Any]:
    db_path = PROJECT_ROOT / ".codegraph" / "codegraph.db"
    detail: dict[str, Any] = {"db": ".codegraph/codegraph.db"}
    if not db_path.is_file():
        return _result(
            "down",
            False,
            detail,
            "codegraph index not found — run codegraph init to build .codegraph/codegraph.db",
        )

    try:
        size = db_path.stat().st_size
        connection = sqlite3.connect(
            f"file:{db_path}?mode=ro", uri=True, timeout=SQLITE_TIMEOUT_SECONDS
        )
        try:
            counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("nodes", "edges", "files")
            }
        finally:
            connection.close()
    except (sqlite3.Error, OSError) as exc:
        return _result(
            "down",
            False,
            {**detail, "error": type(exc).__name__},
            "codegraph database could not be read read-only — measurement failed",
        )

    pid_path = PROJECT_ROOT / ".codegraph" / "daemon.pid"
    daemon_running = False
    try:
        pid = int(json.loads(pid_path.read_text(encoding="utf-8"))["pid"])
        daemon_running = Path(f"/proc/{pid}").exists()
    except (OSError, ValueError, KeyError, TypeError):
        daemon_running = False

    detail.update(
        {
            "size_mb": round(size / 1_048_576, 1),
            "db_mtime": _iso(db_path.stat().st_mtime),
            "daemon_running": daemon_running,
            **counts,
        }
    )
    return _result("ok", True, detail, None)


DEFAULT_PROBES = {
    "busd": probe_busd,
    "cto": probe_cto,
    "content": probe_content,
    "mcp_freshness": probe_mcp_freshness,
    "git": probe_git,
    "browse": probe_browse,
    "codegraph": probe_codegraph,
}

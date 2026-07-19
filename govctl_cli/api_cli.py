"""
govctl api CLI — start / stop / status for the FastAPI server.

Integrates with:
  - uvicorn subprocess management (PID-file based daemon)
  - Port management (default 8765)

Usage:
    govctl api start         # Start server in background
    govctl api start --port 9876 --reload
    govctl api stop          # Stop server
    govctl api status        # Check server status
"""
from __future__ import annotations

import os
import sys
import time
import signal
import logging
from pathlib import Path

try:
    import typer
except ImportError:
    typer = None  # type: ignore[assignment]

log = logging.getLogger("govctl.api")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PID_DIR = Path.home() / ".govctl"
PID_FILE = PID_DIR / "api.pid"
LOG_FILE = PID_DIR / "api.log"
DEFAULT_PORT = 8765

PID_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_pid() -> int | None:
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except (ValueError, OSError):
            pass
    return None


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _write_pid(pid: int) -> None:
    PID_FILE.write_text(str(pid))


def _start_server(port: int = DEFAULT_PORT, reload: bool = False) -> None:
    """Start uvicorn as a background subprocess (daemon)."""
    import subprocess
    cmd = [
        sys.executable, "-m", "uvicorn",
        "govctl_cli.api.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
    ]
    if reload:
        cmd.append("--reload")

    log_fh = open(LOG_FILE, "a")  # noqa: SIM115 — kept open for subprocess

    proc = subprocess.Popen(
        cmd,
        stdout=log_fh,
        stderr=log_fh,
        start_new_session=True,
    )

    _write_pid(proc.pid)
    print(f"✅ API server started (PID {proc.pid}) on http://0.0.0.0:{port}")
    print(f"   Logs: {LOG_FILE}")
    print(f"   Docs: http://localhost:{port}/docs")


# ---------------------------------------------------------------------------
# subprocess import (deferred so `govctl --help` doesn't require uvicorn)
# ---------------------------------------------------------------------------

_UVICORN_AVAILABLE: bool | None = None


def _check_uvicorn() -> bool:
    global _UVICORN_AVAILABLE
    if _UVICORN_AVAILABLE is not None:
        return _UVICORN_AVAILABLE
    try:
        import subprocess  # noqa: F401 — ensure built-in
        import uvicorn  # noqa: F401 — check installed
        _UVICORN_AVAILABLE = True
    except ImportError:
        _UVICORN_AVAILABLE = False
    return _UVICORN_AVAILABLE


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def cmd_start(port: int = DEFAULT_PORT, reload: bool = False) -> None:
    """Start the API server as a background daemon."""
    import subprocess  # built-in

    existing_pid = _read_pid()
    if existing_pid and _is_running(existing_pid):
        print(f"⚠️  API server is already running (PID {existing_pid})")
        print(f"   Stop first:  govctl api stop")
        return

    if not _check_uvicorn():
        print("❌ uvicorn is not installed.")
        print("   Install: pip install uvicorn[standard]")
        return

    _start_server(port=port, reload=reload)


def cmd_stop() -> None:
    """Stop the API server gracefully (SIGTERM → SIGKILL fallback)."""
    pid = _read_pid()
    if not pid:
        print("ℹ️  API server is not running (no PID file)")
        return

    if not _is_running(pid):
        print(f"ℹ️  API server PID {pid} is already dead")
        PID_FILE.unlink(missing_ok=True)
        return

    print(f"🛑 Stopping API server (PID {pid}) …")
    os.kill(pid, signal.SIGTERM)

    for _ in range(10):
        time.sleep(0.3)
        if not _is_running(pid):
            break
    else:
        print(f"⚠️  SIGTERM did not stop PID {pid} — sending SIGKILL")
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.3)

    PID_FILE.unlink(missing_ok=True)
    print("✅ API server stopped")


def cmd_status() -> dict:
    """Show API server status."""
    pid = _read_pid()
    alive = pid is not None and _is_running(pid)
    info = {
        "running": alive,
        "pid": pid if alive else None,
        "pid_file": str(PID_FILE),
        "log_file": str(LOG_FILE),
        "port": DEFAULT_PORT,
    }

    if alive:
        print(f"✅ API server is RUNNING (PID {pid})")
        print(f"   Port: {DEFAULT_PORT}")
        print(f"   PID file: {PID_FILE}")
        print(f"   Logs: {LOG_FILE}")
    else:
        print("ℹ️  API server is NOT running")

    return info


# ---------------------------------------------------------------------------
# Typer sub-app
# ---------------------------------------------------------------------------

if typer is not None:

    api_app = typer.Typer(name="api", help="Start/stop/status FastAPI server")

    @api_app.command()
    def start(
        port: int = typer.Option(DEFAULT_PORT, "--port", "-p", help="Port number"),
        reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
    ):
        """Start the API server as a background daemon."""
        cmd_start(port=port, reload=reload)

    @api_app.command()
    def stop():
        """Stop the API server."""
        cmd_stop()

    @api_app.command()
    def status():
        """Show API server status."""
        cmd_status()

else:
    api_app = None  # type: ignore[assignment]

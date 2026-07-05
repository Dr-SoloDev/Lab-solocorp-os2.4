"""
govctl-bridge: Watch gov/ TOML artifacts and publish to Central Bus.

Usage:
    python -m govctl_cli.bridge start          # Watch mode (foreground)
    python -m govctl_cli.bridge publish <path>  # Publish one artifact
    python -m govctl_cli.bridge status          # Check daemon status
    python -m govctl_cli.bridge stop            # Stop daemon
"""

import os
import sys
import time
import signal
import tomllib
import logging
import uuid
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from central_bus.models import BusMessage
from central_bus.queue import enqueue

# AO Bridge (optional — graceful degradation ถ้า import ล้มเหลว)
try:
    from .ao import ao_listener_loop, process_ao_queue
    _AO_AVAILABLE = True
except ImportError:
    _AO_AVAILABLE = False
    ao_listener_loop = None  # type: ignore[assignment]
    process_ao_queue = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GOV_DIR = Path("gov")
PID_DIR = Path.home() / ".govctl"
PID_FILE = PID_DIR / "bridge.pid"
LOG_FILE = PID_DIR / "bridge.log"
POLL_INTERVAL = 2  # seconds between polls

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

PID_DIR.mkdir(parents=True, exist_ok=True)

_log_handler = logging.FileHandler(LOG_FILE)
_log_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
))
_log_handler.setLevel(logging.DEBUG)

_console_handler = logging.StreamHandler(sys.stderr)
_console_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
))
_console_handler.setLevel(logging.INFO)

log = logging.getLogger("govctl-bridge")
log.setLevel(logging.DEBUG)
log.addHandler(_log_handler)
log.addHandler(_console_handler)

# ---------------------------------------------------------------------------
# Helpers — classify artifact type from path
# ---------------------------------------------------------------------------

def _classify_artifact(path: Path) -> str:
    """Return 'adr', 'rfc', 'guard', or 'unknown'."""
    name = path.name
    parts_lower = [p.lower() for p in path.parts]
    if "adr" in parts_lower or name.startswith("ADR-"):
        return "adr"
    if "rfc" in parts_lower or name.startswith("RFC-"):
        return "rfc"
    # match 'guard' or 'guards' directory
    if any(p in ("guard", "guards") for p in parts_lower):
        return "guard"
    return "unknown"


def _normalize_status(status: str) -> str:
    return status.strip().lower()


# ---------------------------------------------------------------------------
# Gov-event detection per artifact type
# ---------------------------------------------------------------------------

def _detect_adr_event(toml_data: dict) -> str:
    status = _normalize_status(toml_data.get("metadata", {}).get("status", ""))
    if status in ("superseded", "deprecated"):
        return "adr_superseded"
    if status in ("accepted", "approved"):
        return "adr_accepted"
    return "adr_created"


def _detect_rfc_event(toml_data: dict) -> str:
    status = _normalize_status(toml_data.get("metadata", {}).get("status", ""))
    if status == "approved":
        return "rfc_approved"
    if status == "rejected":
        return "rfc_rejected"
    return "rfc_created"


def _detect_guard_event(toml_data: dict) -> str:
    status = _normalize_status(toml_data.get("metadata", {}).get("status", ""))
    if status == "passed":
        return "guard_passed"
    if status == "failed":
        return "guard_failed"
    return "guard_run"


# ---------------------------------------------------------------------------
# BusMessage builder
# ---------------------------------------------------------------------------

def build_message(toml_path: Path, gov_event: str, toml_data: dict) -> BusMessage:
    """Create a BusMessage from a parsed TOML artifact."""
    artifact_type = _classify_artifact(toml_path)
    meta = toml_data.get("metadata", {})
    classification = toml_data.get("classification", {})

    project_id = meta.get("id", toml_path.stem)
    trace_id = str(uuid.uuid4())

    payload = {
        "gov_event": gov_event,
        "artifact_type": artifact_type,
        "artifact_id": meta.get("id", ""),
        "title": meta.get("title", ""),
        "status": meta.get("status", ""),
        "author": meta.get("author", ""),
        "version": meta.get("version", ""),
        "date": meta.get("date", meta.get("created", "")),
        "domain": classification.get("domain", ""),
        "impact": classification.get("impact", ""),
        "complexity": classification.get("complexity", ""),
        "scope": classification.get("scope", ""),
        "path": str(toml_path.resolve()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return BusMessage(
        from_dept="architect",
        to_dept="orchestrator",
        type="ARTIFACT",
        project_id=project_id,
        phase="governance",
        payload=payload,
        trace_id=trace_id,
        priority="normal",
    )


# ---------------------------------------------------------------------------
# Publish — parse TOML → BusMessage → enqueue
# ---------------------------------------------------------------------------

def publish_to_bus(toml_path: Path) -> str:
    """Parse TOML → BusMessage → enqueue to Central Bus.

    Returns the message ID.
    """
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    artifact_type = _classify_artifact(toml_path)

    if artifact_type == "adr":
        gov_event = _detect_adr_event(data)
    elif artifact_type == "rfc":
        gov_event = _detect_rfc_event(data)
    elif artifact_type == "guard":
        gov_event = _detect_guard_event(data)
    else:
        gov_event = "unknown_artifact"

    msg = build_message(toml_path, gov_event, data)
    enqueue(msg)
    log.info("Published %s — %s (%s)", gov_event, msg.id, toml_path.name)
    return msg.id


# ---------------------------------------------------------------------------
# AO config loader
# ---------------------------------------------------------------------------

def _load_ao_config(gov_dir: Path = GOV_DIR) -> dict:
    """Load AO config from gov/ao_config.toml. Returns empty dict on failure."""
    ao_cfg_path = gov_dir / "ao_config.toml"
    if not ao_cfg_path.exists():
        return {}

    try:
        with open(ao_cfg_path, "rb") as f:
            full = tomllib.load(f)
        ao = full.get("ao", {})
        bus = full.get("bus", {})
        agents = full.get("agents", {})

        return {
            "enabled": ao.get("enabled", False),
            "cli_path": ao.get("cli_path", "agent_orchestrator"),
            "timeout_seconds": ao.get("timeout_seconds", 120),
            "max_concurrent": ao.get("max_concurrent", 3),
            "poll_interval": bus.get("poll_interval", 2.0),
            "agents": {k: v for k, v in agents.items() if isinstance(v, dict) and v.get("enabled", False)},
        }
    except (tomllib.TOMLDecodeError, OSError) as exc:
        log.warning("Failed to load AO config: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# AO listener thread management
# ---------------------------------------------------------------------------

_ao_thread: Optional[threading.Thread] = None
_ao_stop_event = threading.Event()


def _start_ao_listener(gov_dir: Path = GOV_DIR) -> None:
    """Start AO listener in a daemon thread."""
    global _ao_thread

    if not _AO_AVAILABLE:
        log.warning("AO bridge not available (import failed) — skipping listener")
        return

    config = _load_ao_config(gov_dir)
    if not config.get("enabled", False):
        log.info("AO bridge disabled in config — skipping listener")
        return

    if _ao_thread is not None and _ao_thread.is_alive():
        log.info("AO listener thread already running")
        return

    _ao_stop_event.clear()

    poll_interval = config.get("poll_interval", 2.0)
    _ao_thread = threading.Thread(
        target=ao_listener_loop,
        kwargs={
            "config": config,
            "poll_interval": poll_interval,
            "stop_event": _ao_stop_event,
        },
        name="ao-listener",
        daemon=True,
    )
    _ao_thread.start()
    log.info("AO listener thread started (poll every %.1fs)", poll_interval)


def _stop_ao_listener(timeout: float = 5.0) -> None:
    """Signal the AO listener to stop and wait for it."""
    global _ao_thread

    if _ao_thread is None or not _ao_thread.is_alive():
        log.info("AO listener not running")
        _ao_thread = None
        return

    log.info("Stopping AO listener thread ...")
    _ao_stop_event.set()
    _ao_thread.join(timeout=timeout)

    if _ao_thread.is_alive():
        log.warning("AO listener thread did not stop within %.1fs", timeout)
    else:
        log.info("AO listener thread stopped")
    _ao_thread = None


# ---------------------------------------------------------------------------
# Polling watch loop
# ---------------------------------------------------------------------------

def _publish_existing(dir_path: Path) -> None:
    """Publish all existing .toml artifacts in a directory."""
    if not dir_path.exists():
        return
    for p in sorted(dir_path.glob("*.toml")):
        try:
            publish_to_bus(p)
        except Exception as exc:
            log.warning("Failed to publish %s: %s", p.name, exc)


def _get_snapshot(dir_path: Path) -> dict[str, float]:
    """Return {filename: mtime} for all .toml files under *dir*."""
    snapshot: dict[str, float] = {}
    if dir_path.exists():
        for p in dir_path.glob("*.toml"):
            snapshot[p.name] = p.stat().st_mtime
    return snapshot


def watch_loop(gov_dir: Path) -> None:
    """Polling watch loop — detects new/changed .toml files and publishes.

    Also starts the AO listener thread if enabled in config.
    """
    log.info("Starting govctl-bridge watch on %s", gov_dir.resolve())

    adr_dir = gov_dir / "adr"
    rfc_dir = gov_dir / "rfc"
    guard_dir = gov_dir / "guards"

    # Snapshot current state
    prev_adr = _get_snapshot(adr_dir)
    prev_rfc = _get_snapshot(rfc_dir)
    prev_guard = _get_snapshot(guard_dir)

    # Publish everything that already exists on first cycle
    log.info("Publishing existing artifacts …")
    _publish_existing(adr_dir)
    _publish_existing(rfc_dir)
    _publish_existing(guard_dir)

    # Start AO listener thread (if enabled in config)
    _start_ao_listener(gov_dir)

    log.info("Watching for changes (poll every %ss) …", POLL_INTERVAL)

    try:
        while True:
            time.sleep(POLL_INTERVAL)

            # ADR
            curr_adr = _get_snapshot(adr_dir)
            for name, mtime in curr_adr.items():
                if name not in prev_adr or prev_adr[name] != mtime:
                    try:
                        publish_to_bus(adr_dir / name)
                    except Exception as exc:
                        log.error("Error publishing %s: %s", name, exc)
            prev_adr = curr_adr

            # RFC
            curr_rfc = _get_snapshot(rfc_dir)
            for name, mtime in curr_rfc.items():
                if name not in prev_rfc or prev_rfc[name] != mtime:
                    try:
                        publish_to_bus(rfc_dir / name)
                    except Exception as exc:
                        log.error("Error publishing %s: %s", name, exc)
            prev_rfc = curr_rfc

            # Guards
            curr_guard = _get_snapshot(guard_dir)
            for name, mtime in curr_guard.items():
                if name not in prev_guard or prev_guard[name] != mtime:
                    try:
                        publish_to_bus(guard_dir / name)
                    except Exception as exc:
                        log.error("Error publishing %s: %s", name, exc)
            prev_guard = curr_guard

    except KeyboardInterrupt:
        log.info("Bridge watcher stopped (Ctrl+C).")
    finally:
        _stop_ao_listener()


# ---------------------------------------------------------------------------
# Daemon lifecycle (PID-file based)
# ---------------------------------------------------------------------------

def _write_pid(pid: int) -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(pid))


def _read_pid() -> Optional[int]:
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


def daemon_start(gov_dir: Path = GOV_DIR, detach: bool = True) -> None:
    """Start the bridge daemon (fork into background if *detach* is True)."""
    existing_pid = _read_pid()
    if existing_pid and _is_running(existing_pid):
        log.warning("Bridge is already running (PID %d)", existing_pid)
        return

    if not detach:
        log.info("Starting bridge in foreground …")
        watch_loop(gov_dir)
        return

    # --- daemonize via double-fork ---
    pid = os.fork()
    if pid > 0:
        # First parent exits immediately
        _write_pid(pid)
        log.info("Bridge daemon started (PID %d)", pid)
        return

    # First child — become session leader
    os.setsid()

    # Second fork — fully detach from terminal
    pid2 = os.fork()
    if pid2 > 0:
        os._exit(0)

    _write_pid(os.getpid())

    # Redirect stdio to /dev/null (log goes to file)
    with open(os.devnull, "w") as null:
        os.dup2(null.fileno(), sys.stdin.fileno())
        os.dup2(null.fileno(), sys.stdout.fileno())
        os.dup2(null.fileno(), sys.stderr.fileno())

    # Start AO listener in detached mode
    _start_ao_listener(gov_dir)

    watch_loop(gov_dir)


def daemon_stop() -> None:
    """Stop the bridge daemon gracefully (SIGTERM → SIGKILL fallback)."""
    pid = _read_pid()
    if not pid:
        log.warning("Bridge is not running (no PID file)")
        return

    if not _is_running(pid):
        log.info("Bridge PID %d is already dead", pid)
        PID_FILE.unlink(missing_ok=True)
        return

    log.info("Stopping bridge daemon (PID %d) …", pid)
    os.kill(pid, signal.SIGTERM)

    # Also stop AO listener thread
    _stop_ao_listener()

    for _ in range(10):
        time.sleep(0.3)
        if not _is_running(pid):
            break
    else:
        log.warning("SIGTERM did not stop PID %d — sending SIGKILL", pid)
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.3)

    PID_FILE.unlink(missing_ok=True)
    log.info("Bridge daemon stopped.")


def daemon_status() -> dict:
    """Return status dict: {running, pid, pid_file}."""
    pid = _read_pid()
    alive = pid is not None and _is_running(pid)
    return {
        "running": alive,
        "pid": pid if alive else None,
        "pid_file": str(PID_FILE),
    }


# ---------------------------------------------------------------------------
# CLI callables (used by cli.py)
# ---------------------------------------------------------------------------

def cmd_start(gov_dir: Path = GOV_DIR, detach: bool = True) -> None:
    daemon_start(gov_dir, detach=detach)


def cmd_stop() -> None:
    daemon_stop()


def cmd_status() -> dict:
    status = daemon_status()
    if status["running"]:
        log.info("Bridge is running (PID %d)", status["pid"])
    else:
        log.info("Bridge is not running")
    return status


def cmd_publish(toml_path: Path) -> str:
    """Publish a single TOML artifact to the Central Bus.  Returns msg id."""
    if not toml_path.exists():
        log.error("File not found: %s", toml_path)
        sys.exit(1)
    if toml_path.suffix != ".toml":
        log.error("Not a .toml file: %s", toml_path)
        sys.exit(1)

    msg_id = publish_to_bus(toml_path)
    print(f"Published {toml_path.name} → message ID: {msg_id}")
    return msg_id


# ---------------------------------------------------------------------------
# AO bridge commands
# ---------------------------------------------------------------------------

def cmd_ao_start(gov_dir: Path = GOV_DIR) -> None:
    """Start the AO bridge listener."""
    config = _load_ao_config(gov_dir)
    if not config.get("enabled", False):
        log.warning("AO bridge is disabled in config — enable [ao].enabled = true in gov/ao_config.toml")
        return
    _start_ao_listener(gov_dir)


def cmd_ao_stop() -> None:
    """Stop the AO bridge listener."""
    _stop_ao_listener()


def cmd_ao_status() -> dict:
    """Show AO bridge listener status."""
    global _ao_thread
    alive = _ao_thread is not None and _ao_thread.is_alive()
    config = _load_ao_config()
    return {
        "running": alive,
        "enabled": config.get("enabled", False),
        "thread_name": _ao_thread.name if alive else None,
        "config": {
            "cli_path": config.get("cli_path", "agent_orchestrator"),
            "poll_interval": config.get("poll_interval", 2.0),
            "max_concurrent": config.get("max_concurrent", 3),
        } if config else None,
    }


# ---------------------------------------------------------------------------
# Typer sub-app for govctl CLI integration
# ---------------------------------------------------------------------------

try:
    import typer as _typer

    bridge_app = _typer.Typer(name="bridge", help="Bridge gov/ TOML artifacts to Central Bus")

    @bridge_app.command()
    def start(
        detach: bool = _typer.Option(True, "--detach/--foreground", help="Run as daemon (background)"),
        gov_dir: Path = _typer.Option(GOV_DIR, "--dir", "-d", help="gov/ directory"),
    ):
        """Start the bridge watcher daemon."""
        cmd_start(gov_dir, detach=detach)

    @bridge_app.command()
    def stop():
        """Stop the bridge daemon."""
        cmd_stop()

    @bridge_app.command()
    def status():
        """Show bridge daemon status."""
        result = cmd_status()
        if result["running"]:
            _typer.echo(f"Bridge is running (PID {result['pid']})")
        else:
            _typer.echo("Bridge is not running")

    @bridge_app.command()
    def publish(
        path: Path = _typer.Argument(..., help="Path to .toml artifact", exists=True),
    ):
        """Publish a single TOML artifact to Central Bus."""
        cmd_publish(path)

    # --- AO subcommands ---

    @bridge_app.command()
    def ao_start(
        gov_dir: Path = _typer.Option(GOV_DIR, "--dir", "-d", help="gov/ directory"),
    ):
        """Start the AO bridge listener."""
        cmd_ao_start(gov_dir)

    @bridge_app.command()
    def ao_stop():
        """Stop the AO bridge listener."""
        cmd_ao_stop()

    @bridge_app.command()
    def ao_status():
        """Show AO bridge listener status."""
        result = cmd_ao_status()
        if result["running"]:
            _typer.echo(f"AO listener is RUNNING (enabled={result['enabled']})")
            _typer.echo(f"  Thread: {result['thread_name']}")
        elif result["enabled"]:
            _typer.echo("AO listener is STOPPED (enabled in config)")
        else:
            _typer.echo("AO listener is DISABLED (set [ao].enabled = true in gov/ao_config.toml)")

        cfg = result.get("config")
        if cfg:
            _typer.echo(f"  CLI: {cfg['cli_path']}")
            _typer.echo(f"  Poll: {cfg['poll_interval']}s")
            _typer.echo(f"  Max concurrent: {cfg['max_concurrent']}")

except ImportError:
    # typer not available — bridge_app will not be registered via CLI,
    # but the module can still be used via python -m govctl_cli.bridge
    bridge_app = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Direct invocation:  python -m govctl_cli.bridge <command>
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="govctl-bridge",
        description="govctl-bridge: watch gov/ TOML artifacts and publish to Central Bus",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("start", help="Start the bridge watcher (daemon)")

    sub.add_parser("stop", help="Stop the bridge daemon")

    sub.add_parser("status", help="Check if the bridge daemon is running")

    pub = sub.add_parser("publish", help="Publish a single TOML artifact")
    pub.add_argument("path", type=Path, help="Path to the .toml file")

    # AO subcommands
    sub.add_parser("ao-start", help="Start the AO bridge listener")
    sub.add_parser("ao-stop", help="Stop the AO bridge listener")
    sub.add_parser("ao-status", help="Show AO bridge listener status")

    args = parser.parse_args()

    if args.command == "start":
        cmd_start()
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "status":
        cmd_status()
    elif args.command == "publish":
        cmd_publish(args.path)
    elif args.command == "ao-start":
        cmd_ao_start()
    elif args.command == "ao-stop":
        cmd_ao_stop()
    elif args.command == "ao-status":
        result = cmd_ao_status()
        print(f"Running: {result['running']}")
        print(f"Enabled: {result['enabled']}")
        if result.get("config"):
            print(f"CLI: {result['config']['cli_path']}")


if __name__ == "__main__":
    main()

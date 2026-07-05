"""
AO Bridge — Central Bus ↔ AO Adapter integration layer.

Watches for ``BusMessage(type="AO_REQUEST")`` in the Central Bus queue,
spawns the appropriate AO agent adapter, and publishes the response
back as ``BusMessage(type="AO_RESPONSE")``.

Designed to be called from the existing govctl bridge daemon's watch loop,
or run as a standalone polling loop.

Usage:
    # As part of govctl bridge
    python -m govctl_cli.ao.bridge start

    # One-shot process
    from govctl_cli.ao.bridge import process_queue
    process_queue()
"""

from __future__ import annotations

import os
import sys
import time
import signal
import logging
from pathlib import Path
from typing import Optional

from central_bus.models import BusMessage
from central_bus.queue import dequeue, enqueue
import asyncio
from central_bus.audit import log as _audit_log_coro


def _audit_sync(msg) -> None:
    """Fire-and-forget audit write from a sync context (no running loop)."""
    try:
        asyncio.run(_audit_log_coro(msg))
    except Exception as exc:  # noqa: BLE001
        log.warning("audit write failed: %s", exc)


audit_log = _audit_sync
from .adapter import (
    process_ao_request,
    AO_REQUEST_TYPE,
    AO_RESPONSE_TYPE,
    AO_ERROR_TYPE,
    REGISTRY,
    list_agents,
)

log = logging.getLogger("govctl.ao.bridge")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PID_DIR = Path.home() / ".govctl"
PID_FILE = PID_DIR / "ao_bridge.pid"
POLL_INTERVAL = 1.0  # seconds between queue polls

# ---------------------------------------------------------------------------
# Core — process one AO_REQUEST message
# ---------------------------------------------------------------------------


def handle_ao_message(msg: BusMessage) -> BusMessage | None:
    """Process one AO_REQUEST BusMessage and return the response BusMessage.

    Returns None if the message is not an AO_REQUEST or processing failed.
    """
    if msg.type != AO_REQUEST_TYPE:
        return None

    trace_id = msg.trace_id
    agent_id = msg.payload.get("agent_id", "unknown")
    log.info("[%s] Handling AO_REQUEST agent=%s project=%s",
             trace_id, agent_id, msg.project_id)

    # Delegate to adapter layer
    response_payload = process_ao_request(msg)

    # Determine response type based on status
    response_type = AO_RESPONSE_TYPE
    if response_payload and response_payload.get("status") == "error":
        response_type = AO_ERROR_TYPE

    # Build response BusMessage
    response = BusMessage(
        from_dept="orchestrator",
        to_dept=msg.from_dept,  # reply to whoever requested
        type=response_type,
        project_id=msg.project_id,
        phase=msg.phase,
        payload=response_payload or {
            "agent_id": agent_id,
            "trace_id": trace_id,
            "status": "error",
            "error": "process_ao_request returned None",
        },
        trace_id=trace_id,
        priority=msg.priority,
    )

    # Audit trail
    audit_log(msg)      # log the original request
    audit_log(response)  # log the response

    # Enqueue response
    enqueue(response)
    log.info("[%s] Published AO_RESPONSE (%s) for agent=%s",
             trace_id, response.id, agent_id)

    return response


# ---------------------------------------------------------------------------
# Queue processing loop
# ---------------------------------------------------------------------------


def process_queue(batch_size: int = 10) -> int:
    """Dequeue and process up to *batch_size* AO_REQUEST messages.

    Returns the count of messages processed.
    """
    count = 0
    for _ in range(batch_size):
        msg = dequeue("high") or dequeue("normal") or dequeue("low")
        if msg is None:
            break
        if msg.type != AO_REQUEST_TYPE:
            continue  # not for us — leave it in the queue (but we already dequeued…)
            # TODO: re-enqueue non-AO messages so another consumer can grab them
        handle_ao_message(msg)
        count += 1
    return count


def watch_loop():
    """Polling loop — continuously processes AO_REQUEST messages."""
    log.info("Starting AO bridge watcher …")
    log.info("Registered agents: %s", ", ".join(sorted(REGISTRY.keys())))

    try:
        while True:
            processed = process_queue(batch_size=5)
            if processed:
                log.debug("Processed %d AO_REQUEST message(s)", processed)
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        log.info("AO bridge watcher stopped (Ctrl+C).")


# ---------------------------------------------------------------------------
# Daemon lifecycle
# ---------------------------------------------------------------------------


def _write_pid(pid: int) -> None:
    PID_DIR.mkdir(parents=True, exist_ok=True)
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


def daemon_start(detach: bool = True) -> None:
    """Start the AO bridge daemon (background by default)."""
    existing_pid = _read_pid()
    if existing_pid and _is_running(existing_pid):
        log.warning("AO bridge is already running (PID %d)", existing_pid)
        return

    if not detach:
        log.info("Starting AO bridge in foreground …")
        watch_loop()
        return

    # Daemonize via double-fork
    pid = os.fork()
    if pid > 0:
        _write_pid(pid)
        log.info("AO bridge daemon started (PID %d)", pid)
        return

    os.setsid()
    pid2 = os.fork()
    if pid2 > 0:
        os._exit(0)

    _write_pid(os.getpid())
    with open(os.devnull, "w") as null:
        os.dup2(null.fileno(), sys.stdin.fileno())
        os.dup2(null.fileno(), sys.stdout.fileno())
        os.dup2(null.fileno(), sys.stderr.fileno())

    watch_loop()


def daemon_stop() -> None:
    """Stop the AO bridge daemon."""
    pid = _read_pid()
    if not pid:
        log.warning("AO bridge is not running (no PID file)")
        return

    if not _is_running(pid):
        log.info("AO bridge PID %d is already dead", pid)
        PID_FILE.unlink(missing_ok=True)
        return

    log.info("Stopping AO bridge daemon (PID %d) …", pid)
    os.kill(pid, signal.SIGTERM)
    for _ in range(10):
        time.sleep(0.3)
        if not _is_running(pid):
            break
    else:
        log.warning("SIGTERM did not stop PID %d — sending SIGKILL", pid)
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.3)

    PID_FILE.unlink(missing_ok=True)
    log.info("AO bridge daemon stopped.")


def daemon_status() -> dict:
    pid = _read_pid()
    alive = pid is not None and _is_running(pid)
    return {
        "running": alive,
        "pid": pid if alive else None,
        "pid_file": str(PID_FILE),
    }


# ---------------------------------------------------------------------------
# CLI callables
# ---------------------------------------------------------------------------


def cmd_start(detach: bool = True) -> None:
    daemon_start(detach=detach)


def cmd_stop() -> None:
    daemon_stop()


def cmd_status() -> dict:
    status = daemon_status()
    if status["running"]:
        log.info("AO bridge is running (PID %d)", status["pid"])
    else:
        log.info("AO bridge is not running")
    return status


def cmd_process(batch_size: int = 5) -> int:
    """One-shot: process up to *batch_size* AO_REQUEST messages."""
    count = process_queue(batch_size=batch_size)
    log.info("Processed %d AO_REQUEST message(s)", count)
    return count


# ---------------------------------------------------------------------------
# Direct invocation
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="govctl-ao-bridge",
        description="AO bridge: process AO_REQUEST messages from Central Bus",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("start", help="Start the AO bridge daemon")
    sub.add_parser("stop", help="Stop the AO bridge daemon")
    sub.add_parser("status", help="Check AO bridge daemon status")

    proc = sub.add_parser("process", help="One-shot: process queued AO requests")
    proc.add_argument("--batch", type=int, default=5, help="Max messages to process")

    args = parser.parse_args()

    if args.command == "start":
        cmd_start()
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "status":
        cmd_status()
    elif args.command == "process":
        cmd_process(args.batch)


if __name__ == "__main__":
    main()

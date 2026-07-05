"""
AO Bridge Integration — Central Bus ↔ Agent Orchestrator

Bridge functions ที่เชื่อม Central Bus กับ AO:
  - handle_ao_request(msg)    — BusMessage → spawn agent → BusMessage
  - publish_ao_event(...)     — audit trail publish
  - ao_listener_loop(...)     — polling loop สำหรับ threading
  - process_ao_queue(...)     — one-shot processing

Architecture:
    Central Bus (queue.jsonl)
         │
         ▼  (poll for type="AO_REQUEST")
    handle_ao_request()
         │
         ├── publish_ao_event("agent_spawned")
         ├── adapter.process_ao_request()   → AgentAdapter.invoke()
         │                                       └── AOClient.invoke()
         ├── publish_ao_event("agent_completed" / "agent_failed")
         └── enqueue(AO_RESPONSE)

Relies on:
    - adapter layer (adapter.py) for agent-specific prompt/parse
    - client layer (client.py) for AO CLI subprocess
    - Central Bus (central_bus) for queue + message types
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from central_bus.models import BusMessage
from central_bus.queue import enqueue, dequeue

from .client import AOClient, AOCliClient, AO_LOG_DIR

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_handler = logging.FileHandler(AO_LOG_DIR / "ao.log")
_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] AO-BRIDGE: %(message)s",
))
_handler.setLevel(logging.DEBUG)

log = logging.getLogger("govctl-ao-bridge")
log.setLevel(logging.DEBUG)
log.addHandler(_handler)


# ---------------------------------------------------------------------------
# Lazy client singleton (separate from the AOCliClient in client.py)
# ---------------------------------------------------------------------------

_bridge_client: Optional[AOCliClient] = None


def _get_bridge_client(config: Optional[dict] = None) -> AOCliClient:
    """Get or create bridge's AOCliClient singleton."""
    global _bridge_client
    if _bridge_client is None:
        cli_path = (config or {}).get("cli_path", "agent_orchestrator")
        timeout = (config or {}).get("timeout_seconds", 120)
        _bridge_client = AOCliClient(cli_path=cli_path, timeout=timeout)
    return _bridge_client


def reset_bridge_client() -> None:
    """Reset bridge client singleton (testing / config reload)."""
    global _bridge_client
    _bridge_client = None


# ---------------------------------------------------------------------------
# Core: handle_ao_request
# ---------------------------------------------------------------------------

def handle_ao_request(msg: BusMessage, config: Optional[dict] = None) -> BusMessage:
    """รับ BusMessage type="AO_REQUEST" → spawn agent → สร้าง AO_RESPONSE

    Payload ที่คาดหวังใน ``msg.payload``:
        agent_id (str): **required** ชื่อ agent
        prompt   (str): **required** prompt สำหรับ agent
        timeout  (int):  optional override timeout (วินาที)

    Args:
        msg:    BusMessage with type="AO_REQUEST"
        config: AO config dict (optional, for cli_path/timeout)

    Returns:
        BusMessage type="AO_RESPONSE" ที่ถูก enqueue แล้ว
    """
    agent_id = msg.payload.get("agent_id", "")
    prompt = msg.payload.get("prompt", "")
    timeout = msg.payload.get("timeout")

    # ── Validation ──────────────────────────────────────────────────
    if not agent_id:
        return _error_response(msg, "Missing required field 'agent_id' in payload")
    if not prompt:
        return _error_response(msg, "Missing required field 'prompt' in payload")

    log.info("handle_ao_request: agent=%s trace=%s project=%s",
             agent_id, msg.trace_id, msg.project_id)

    client = _get_bridge_client(config)

    # ── Pre-flight ──────────────────────────────────────────────────
    if not client.check_available():
        return _error_response(
            msg,
            f"AO CLI '{client.cli_path}' is not available. "
            f"Install it or update cli_path in gov/ao_config.toml",
        )

    # ── Publish spawn audit event ───────────────────────────────────
    publish_ao_event(
        agent_id, "agent_spawned",
        {"trace_id": msg.trace_id, "prompt_preview": prompt[:200]},
        project_id=msg.project_id,
    )

    # ── Execute via AOCliClient.run_agent ───────────────────────────
    result = client.run_agent(agent_id, prompt, timeout=timeout)

    # ── Publish completion audit event ──────────────────────────────
    event = "agent_completed" if result["success"] else "agent_failed"
    publish_ao_event(
        agent_id, event,
        {
            "trace_id": msg.trace_id,
            "elapsed": result["elapsed"],
            "return_code": result["return_code"],
            "output_size": len(result.get("output", "")),
        },
        project_id=msg.project_id,
    )

    # ── Build AO_RESPONSE BusMessage ────────────────────────────────
    response = BusMessage(
        from_dept="architect",
        to_dept=msg.from_dept,
        type="AO_RESPONSE",
        project_id=msg.project_id,
        phase=msg.phase,
        payload={
            "request_trace_id": msg.trace_id,
            "request_id": msg.id,
            "agent_id": agent_id,
            "result": {
                "success": result["success"],
                "output": result.get("output", ""),
                "error": result.get("error", ""),
                "elapsed": result.get("elapsed", 0),
                "return_code": result.get("return_code", -1),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        trace_id=msg.trace_id,
        priority=msg.priority,
    )

    enqueue(response)

    status = "OK" if result["success"] else "FAIL"
    log.info("AO_RESPONSE enqueued: trace=%s agent=%s status=%s elapsed=%.2fs",
             msg.trace_id, agent_id, status, result.get("elapsed", 0))

    return response


def _error_response(original: BusMessage, detail: str) -> BusMessage:
    """Build and enqueue an error AO_RESPONSE."""
    log.error("AO_REQUEST error: trace=%s detail=%s", original.trace_id, detail)

    response = BusMessage(
        from_dept="architect",
        to_dept=original.from_dept,
        type="AO_RESPONSE",
        project_id=original.project_id,
        phase=original.phase,
        payload={
            "request_trace_id": original.trace_id,
            "request_id": original.id,
            "error": detail,
            "result": {
                "success": False,
                "output": "",
                "error": detail,
                "elapsed": 0,
                "return_code": -1,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        trace_id=original.trace_id,
        priority=original.priority,
    )

    enqueue(response)
    return response


# ---------------------------------------------------------------------------
# Event publisher (audit trail)
# ---------------------------------------------------------------------------

def publish_ao_event(
    agent_id: str,
    event: str,
    payload: dict,
    project_id: str = "system",
) -> BusMessage:
    """Publish AO event เข้า Central Bus สำหรับ audit trail

    Args:
        agent_id:   ID ของ agent
        event:      ชื่อ event (agent_spawned, agent_completed, agent_failed)
        payload:    ข้อมูลเพิ่มเติม
        project_id: project id (default: "system")

    Returns:
        BusMessage ที่ถูก enqueue แล้ว
    """
    msg = BusMessage(
        from_dept="architect",
        to_dept="orchestrator",
        type="GOVERNANCE",
        project_id=project_id,
        phase="governance",
        payload={
            "gov_event": f"ao_{event}",
            "gov_detail": f"AO agent '{agent_id}' event: {event}",
            "gov_entity_id": agent_id,
            "gov_result": {
                "agent_id": agent_id,
                "event": event,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
        trace_id=payload.get("trace_id", ""),
        priority="normal",
    )

    enqueue(msg)
    log.debug("AO event published: agent=%s event=%s msg_id=%s",
              agent_id, event, msg.id)
    return msg


# ---------------------------------------------------------------------------
# Queue listener — designed for threading
# ---------------------------------------------------------------------------

def ao_listener_loop(
    config: Optional[dict] = None,
    poll_interval: float = 2.0,
    stop_event=None,
) -> None:
    """Polling loop: อ่าน Central Bus queue สำหรับ messages type="AO_REQUEST"

    เมื่อเจอ AO_REQUEST → spawn agent → publish AO_RESPONSE

    ออกแบบให้ใช้กับ ``threading.Thread``:

        import threading
        stop = threading.Event()
        t = threading.Thread(
            target=ao_listener_loop,
            kwargs={"stop_event": stop},
            daemon=True,
        )
        t.start()
        # ... later ...
        stop.set()
        t.join()

    Args:
        config:        dict ที่ merge แล้วจาก ao_config.toml
        poll_interval: วินาทีระหว่าง polls
        stop_event:    threading.Event — set() เพื่อ graceful shutdown
    """
    log.info("AO listener started (poll interval=%.1fs)", poll_interval)

    while True:
        if stop_event and stop_event.is_set():
            log.info("AO listener received stop signal — exiting")
            break

        try:
            # Poll all priorities
            for priority in ("critical", "high", "normal", "low"):
                msg = dequeue(priority)  # type: ignore[arg-type]
                if msg is None:
                    continue
                if msg.type != "AO_REQUEST":
                    enqueue(msg)  # Not for us — put it back
                    continue

                log.info("AO listener dequeued AO_REQUEST: agent=%s trace=%s",
                         msg.payload.get("agent_id"), msg.trace_id)
                handle_ao_request(msg, config)

        except Exception:
            log.exception("AO listener loop error — continuing")

        time.sleep(poll_interval)


def process_ao_queue(
    max_messages: int = 10,
    config: Optional[dict] = None,
) -> int:
    """Process pending AO_REQUEST messages from the queue (non-blocking).

    ใช้สำหรับ one-off processing แทนการรัน listener loop ตลอดเวลา

    Args:
        max_messages: จำนวนสูงสุดที่จะ process
        config:       AO config dict

    Returns:
        จำนวน messages ที่ process แล้ว
    """
    processed = 0
    for priority in ("critical", "high", "normal", "low"):
        for _ in range(max_messages):
            msg = dequeue(priority)  # type: ignore[arg-type]
            if msg is None:
                break
            if msg.type != "AO_REQUEST":
                enqueue(msg)
                continue
            handle_ao_request(msg, config)
            processed += 1
            if processed >= max_messages:
                return processed
    return processed

"""Dispatch management."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from datetime import datetime
from solocorp_skills.core import SolocorpError, SolocorpClient

BUS_DIR = Path(__file__).parent.parent / "bus"


def create_dispatch(
    task: str,
    priority: str = "L2",
    source: str = "system",
    target: str = "all",
    context: Optional[str] = None,
) -> dict:
    """Create a new dispatch record.

    Args:
        task: Task description
        priority: Priority level
        source: Source department
        target: Target department or "all"
        context: Additional context

    Returns:
        Dict with dispatch_id and status
    """
    client = SolocorpClient()
    if client.is_ready():
        try:
            return client._api_post("/v1/dispatches", {
                "task": task,
                "priority": priority,
                "source": source,
                "target": target,
                "context": context,
            })
        except Exception:
            pass

    return _dispatch_local(task, priority, source, target, context)


def get_dispatch(dispatch_id: str) -> dict:
    """Get a dispatch by ID."""
    client = SolocorpClient()
    if client.is_ready():
        try:
            return client._api_get(f"/v1/dispatches/{dispatch_id}")
        except Exception:
            pass

    return _dispatch_local_get(dispatch_id)


def list_dispatches(limit: int = 20) -> list[dict]:
    """List recent dispatches."""
    client = SolocorpClient()
    if client.is_ready():
        try:
            return client._api_get(f"/v1/dispatches?limit={limit}")
        except Exception:
            pass

    return _dispatch_list_local(limit)


def _dispatch_local(task: str, priority: str, source: str, target: str, context: str) -> dict:
    """Fallback to local dispatch."""
    return {
        "dispatch_id": f"disp-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "task": task,
        "priority": priority,
        "source": source,
        "target": target,
        "status": "created",
        "created_at": datetime.now().isoformat(),
    }

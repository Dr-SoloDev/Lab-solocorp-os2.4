"""Queue management."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from solocorp_skills.core import SolocorpError, SolocorpClient

BUS_DIR = Path(__file__).parent.parent / "bus"


def get_queue(queue_name: str = "normal") -> list[dict]:
    """Get items from a queue.

    Args:
        queue_name: Queue name (high, normal, low, dead_letter)

    Returns:
        List of queue items
    """
    client = SolocorpClient()
    if client.is_ready():
        try:
            return client._api_get(f"/v1/queue/{queue_name}")
        except Exception:
            pass

    return _queue_local(queue_name)


def peek_queue(queue_name: str = "normal", count: int = 1) -> list[dict]:
    """Peek at queue items without removing them."""
    return get_queue(queue_name)[:count]


def push_queue(queue_name: str, item: dict) -> dict:
    """Push an item to a queue.

    Args:
        queue_name: Queue name
        item: Item to push (must have 'task' field)

    Returns:
        Push result
    """
    client = SolocorpClient()
    if client.is_ready():
        try:
            return client._api_post(f"/v1/queue/{queue_name}", item)
        except Exception:
            pass

    return _queue_push_local(queue_name, item)


def _queue_local(queue_name: str) -> list[dict]:
    """Fallback to local queue."""
    queue_path = BUS_DIR / "queue" / f"{queue_name}.jsonl"
    if not queue_path.exists():
        return []

    items = []
    for line in queue_path.read_text().strip().split("\n"):
        if line.strip():
            try:
                import json
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def _queue_push_local(queue_name: str, item: dict) -> dict:
    """Fallback push to local queue."""
    queue_path = BUS_DIR / "queue" / f"{queue_name}.jsonl"
    import json
    queue_path.write_text((queue_path.read_text() + "\n" + json.dumps(item)).encode())
    return {"status": "pushed", "queue": queue_name, "item": item}

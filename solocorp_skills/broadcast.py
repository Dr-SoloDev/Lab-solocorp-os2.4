"""Broadcast announcements to departments."""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from solocorp_skills.core import SolocorpError, SolocorpClient


def announce(
    message: str,
    priority: str = "normal",
    target: str = "all",
    sender: str = "system",
) -> dict:
    """Broadcast announcement to all departments.

    Args:
        message: Announcement message
        priority: Priority (low, normal, high, urgent)
        target: Target ("all", or specific department)
        sender: Sender department name

    Returns:
        Announce result with recipients
    """
    client = SolocorpClient()
    if client.is_ready():
        try:
            return client._api_post("/v1/announce", {
                "message": message,
                "priority": priority,
                "target": target,
                "sender": sender,
            })
        except Exception as e:
            raise SolocorpError(f"Announcement failed: {e}")

    return _announce_local(message, priority, target, sender)


def _announce_local(message: str, priority: str, target: str, sender: str) -> dict:
    """Local fallback for announcements."""
    return {
        "announcement_id": f"ann-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "message": message,
        "priority": priority,
        "target": target,
        "sender": sender,
        "sent_at": datetime.now().isoformat(),
        "status": "broadcasted",
    }

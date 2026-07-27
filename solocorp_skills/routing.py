"""Route requests between departments."""

from __future__ import annotations
from typing import Optional
from solocorp_skills.core import SolocorpError, SolocorpClient
from solocorp_skills.departments import get_department

_client = SolocorpClient()


def route_request(
    from_dept: str,
    to_dept: str,
    task: str,
    priority: str = "L2",
    deadline: Optional[str] = None,
    context: Optional[str] = None,
    skills_required: Optional[list[str]] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Route a task from one department to another.

    Args:
        from_dept: Source department name
        to_dept: Target department name
        task: Task description
        priority: L1, L2, L3, L4, or L5
        deadline: ISO format datetime string
        context: Additional context
        skills_required: List of skill names needed
        metadata: Additional metadata

    Returns:
        Dict with dispatch_id, status, and routing info
    """
    if not _client.is_ready():
        return _route_local(from_dept, to_dept, task, priority, deadline, context, skills_required, metadata)

    try:
        return _client._api_post("/v1/route", {
            "from": from_dept,
            "to": to_dept,
            "task": task,
            "priority": priority,
            "deadline": deadline,
            "context": context,
            "skills_required": skills_required,
            "metadata": metadata or {},
        })
    except Exception as e:
        raise SolocorpError(f"Failed to route request: {e}")


def route_to_dept(dept: str, task: str, priority: str = "L2") -> dict:
    """Route a task directly to a department (convenience wrapper).

    Args:
        dept: Target department name
        task: Task description
        priority: Priority level

    Returns:
        Routing result
    """
    dept_info = get_department(dept)
    if not dept_info:
        raise SolocorpError(f"Department '{dept}' not found")

    return route_request(
        from_dept="system",
        to_dept=dept,
        task=task,
        priority=priority,
    )

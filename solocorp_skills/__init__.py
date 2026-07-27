"""
Solocorp Skills — Python module for SoloCorp OS agents.

Provides a clean API for agents to interact with:
- Department routing and communication
- Queue management
- Dispatch tracking
- Project status
- Skill invocation
- Mirror checks
- Broadcasting

Usage:
    from solocorp_skills import route_request, get_department, check_status

    result = route_request(
        from_dept="engineering",
        to_dept="design",
        task="Implement new dashboard UI",
        priority="L2"
    )
"""

from solocorp_skills.core import SolocorpClient
from solocorp_skills.routing import route_request, route_to_dept
from solocorp_skills.departments import get_department, list_departments
from solocorp_skills.status import check_status, project_status
from solocorp_skills.dispatch import create_dispatch, get_dispatch, list_dispatches
from solocorp_skills.queue import get_queue, peek_queue, push_queue
from solocorp_skills.skills import invoke_skill
from solocorp_skills.mirror import mirror_check
from solocorp_skills.broadcast import announce

__all__ = [
    "SolocorpClient",
    "route_request",
    "route_to_dept",
    "get_department",
    "list_departments",
    "check_status",
    "project_status",
    "create_dispatch",
    "get_dispatch",
    "list_dispatches",
    "get_queue",
    "peek_queue",
    "push_queue",
    "invoke_skill",
    "mirror_check",
    "announce",
]

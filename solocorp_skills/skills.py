"""Skill invocation."""

from __future__ import annotations
from typing import Optional
from solocorp_skills.core import SolocorpError, SolocorpClient


def invoke_skill(
    skill_name: str,
    params: Optional[dict] = None,
) -> dict:
    """Invoke a department skill.

    Args:
        skill_name: Skill name (e.g., "ceo/sprint-plan", "engineering/deploy")
        params: Skill parameters

    Returns:
        Skill execution result
    """
    client = SolocorpClient()
    if client.is_ready():
        try:
            return client._api_post(
                f"/v1/skills/{skill_name}",
                params or {}
            )
        except Exception as e:
            raise SolocorpError(f"Skill invocation failed: {e}")

    raise SolocorpError("Central Bus unavailable for skill invocation")

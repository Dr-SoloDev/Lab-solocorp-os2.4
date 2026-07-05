"""
Profile ↔ Agent Mapping + Agent Adapter Registry

Maps all 15 SoloCorp OS departmental profiles (01-ceo to 15-content-creator)
to the 5 core AO agents, and registers concrete AgentAdapter implementations
via the @register decorator.

Mapping rationale:
    - **ceo**          — Strategic decisions, final authority, vision
    - **orchestrator** — Cross-dept coordination, pipeline, governance routing
    - **architect**    — Architecture review, ADR validation, design-system oversight
    - **engineering**  — Technical implementation, sprint planning, code quality
    - **qa**           — Test planning, quality gates, evidence collection

Importing this module triggers auto-registration of all adapters.
"""

# ===================================================================
# Profile → Agent mapping (15 profiles → 5 AO agents)
# ===================================================================

PROFILE_TO_AGENT: dict[str, str] = {
    "01-ceo": "ceo",
    "02-cfo": "orchestrator",       # finance decisions → orchestrator coordination
    "03-cmo": "orchestrator",       # marketing strategy → orchestrator coordination
    "04-orchestrator": "orchestrator",
    "05-architect": "architect",
    "06-product": "orchestrator",   # product planning → orchestrator coordination
    "07-engineering": "engineering",
    "08-design": "architect",       # design system → architect review
    "09-ui-designer": "engineering",
    "10-qa": "qa",
    "11-sales": "orchestrator",     # sales strategy → orchestrator coordination
    "12-support": "engineering",
    "13-legal": "orchestrator",     # legal review → orchestrator coordination
    "14-web3": "engineering",
    "15-content-creator": "engineering",
}

# Reverse mapping: agent → list of profile IDs
AGENT_TO_PROFILES: dict[str, list[str]] = {}
for pid, aid in PROFILE_TO_AGENT.items():
    AGENT_TO_PROFILES.setdefault(aid, []).append(pid)


# ===================================================================
# Lookup helpers
# ===================================================================

def get_agent_for_profile(profile_id: str) -> str:
    """Return the AO agent ID responsible for *profile_id*.

    Args:
        profile_id: e.g. ``"07-engineering"``, ``"02-cfo"``.

    Returns:
        AO agent ID: ``"ceo"`` | ``"orchestrator"`` | ``"architect"`` |
        ``"engineering"`` | ``"qa"``.

    Raises:
        KeyError: If *profile_id* is unknown.
    """
    if profile_id not in PROFILE_TO_AGENT:
        valid = sorted(PROFILE_TO_AGENT.keys())
        raise KeyError(
            f"Unknown profile {profile_id!r}. "
            f"Valid profiles: {', '.join(valid)}"
        )
    return PROFILE_TO_AGENT[profile_id]


def get_profiles_for_agent(agent_id: str) -> list[str]:
    """Return all profile IDs that map to the given AO agent.

    Args:
        agent_id: ``"ceo"`` | ``"orchestrator"`` | ``"architect"`` |
                  ``"engineering"`` | ``"qa"``.

    Returns:
        Sorted list of profile IDs.

    Raises:
        KeyError: If *agent_id* is unknown.
    """
    if agent_id not in AGENT_TO_PROFILES:
        valid = sorted(AGENT_TO_PROFILES.keys())
        raise KeyError(
            f"Unknown agent {agent_id!r}. "
            f"Valid agents: {', '.join(valid)}"
        )
    return list(sorted(AGENT_TO_PROFILES[agent_id]))


# ===================================================================
# Import agent adapters — triggers @register decorators
# ===================================================================

from . import ceo  # noqa: F401
from . import orchestrator  # noqa: F401
from . import architect  # noqa: F401
from . import engineering  # noqa: F401
from . import qa  # noqa: F401

__all__ = [
    "PROFILE_TO_AGENT",
    "AGENT_TO_PROFILES",
    "get_agent_for_profile",
    "get_profiles_for_agent",
]

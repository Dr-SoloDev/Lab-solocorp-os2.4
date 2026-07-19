from dataclasses import dataclass, field
from typing import Literal, Any
from datetime import datetime, timezone
import uuid

Department = Literal[
    "ceo","cfo","cmo","orchestrator","architect","product",
    "engineering","design","ui_designer","qa","sales","support",
    "legal","web3","content_creator","neteng","cybersec","psychology",
]
Priority = Literal["critical","high","normal","low"]
MessageType = Literal[
    "HANDOFF","STATUS","ARTIFACT","EXCEPTION","GOVERNANCE",
    "AO_REQUEST","AO_RESPONSE",
]

# Governance event types that must be present in payload when type=GOVERNANCE
GovernanceEvent = Literal[
    "rfc_created",       # RFC ถูกสร้าง → broadcast to relevant depts
    "adr_accepted",      # ADR ถูก accept → route to architect
    "guard_run",         # Guard check ถูก trigger → route to architect
    "guard_failed",      # Guard check ล้มเหลว → route to orchestrator
    "complexity_assessed", # Complexity score ถูกประเมิน → route to architect
]

GOVERNANCE_EVENT_DOC = """
Payload convention for GOVERNANCE type messages:
    {
        "gov_event": "<GovernanceEvent>",   # required — identifies the governance action
        "gov_detail": "...",                 # required — human-readable detail
        "gov_entity_id": "...",              # optional — RFC-XXX, ADR-XXX, guard name
        "gov_result": {...},                 # optional — result payload (scores, status, etc.)
    }
"""


@dataclass
class BusMessage:
    from_dept: Department
    to_dept: Department
    type: MessageType
    project_id: str
    phase: str
    payload: dict[str, Any]
    trace_id: str
    priority: Priority = "normal"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    retry_count: int = 0

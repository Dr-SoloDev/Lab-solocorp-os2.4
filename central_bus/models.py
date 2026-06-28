from dataclasses import dataclass, field
from typing import Literal, Any
from datetime import datetime, timezone
import uuid

Department = Literal[
    "ceo","cfo","cmo","orchestrator","architect","product",
    "engineering","design","ui_designer","qa","sales","support","legal","web3"
]
Priority = Literal["critical","high","normal","low"]
MessageType = Literal["HANDOFF","STATUS","ARTIFACT","EXCEPTION"]


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

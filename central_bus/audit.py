import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path
from central_bus.models import BusMessage

PROJECTS_DIR = Path(__file__).parent.parent / "bus" / "projects"


def _audit_path(project_id: str) -> Path:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = PROJECTS_DIR / project_id / "audit" / f"{date}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def log(msg: BusMessage) -> None:
    """Append message to audit log (immutable JSONL)."""
    path = _audit_path(msg.project_id)
    line = json.dumps(msg.__dict__) + "\n"
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(line)
        fcntl.flock(f, fcntl.LOCK_UN)


def read(project_id: str, date: str | None = None) -> list[dict]:
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = PROJECTS_DIR / project_id / "audit" / f"{date}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]

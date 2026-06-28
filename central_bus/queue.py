import fcntl
import json
from pathlib import Path
from .models import BusMessage, Priority

QUEUE_DIR = Path(__file__).parent.parent / "bus" / "queue"
MAX_RETRIES = 3


def _queue_file(priority: Priority) -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return QUEUE_DIR / f"{priority}.jsonl"


def enqueue(msg: BusMessage) -> None:
    path = _queue_file(msg.priority)
    line = json.dumps(msg.__dict__) + "\n"
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(line)
        fcntl.flock(f, fcntl.LOCK_UN)


def dequeue(priority: Priority) -> BusMessage | None:
    path = _queue_file(priority)
    if not path.exists():
        return None
    with open(path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        lines = f.readlines()
        if not lines:
            fcntl.flock(f, fcntl.LOCK_UN)
            return None
        first, rest = lines[0], lines[1:]
        f.seek(0)
        f.writelines(rest)
        f.truncate()
        fcntl.flock(f, fcntl.LOCK_UN)
    data = json.loads(first)
    return BusMessage(**data)


def drain(priority: Priority) -> list[BusMessage]:
    msgs = []
    while (m := dequeue(priority)) is not None:
        msgs.append(m)
    return msgs

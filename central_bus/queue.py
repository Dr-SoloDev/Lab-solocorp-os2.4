import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path
from .models import BusMessage, Priority

QUEUE_DIR = Path(__file__).parent.parent / "bus" / "queue"
DEAD_LETTER_DIR = QUEUE_DIR / "dead_letter"
MAX_RETRIES = 3


def _queue_file(priority: Priority, dead_letter: bool = False) -> Path:
    base = DEAD_LETTER_DIR if dead_letter else QUEUE_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{priority}.jsonl"


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


def requeue(msg: BusMessage) -> bool:
    """Requeue with incremented retry count.
    Returns False if MAX_RETRIES exceeded — message moved to dead letter queue.
    """
    msg.retry_count += 1
    if msg.retry_count > MAX_RETRIES:
        _enqueue_dead_letter(msg, "Max retries exceeded")
        return False
    enqueue(msg)
    return True


def _enqueue_dead_letter(msg: BusMessage, reason: str) -> None:
    path = _queue_file(msg.priority, dead_letter=True)
    record = {
        "message": msg.__dict__,
        "reason": reason,
        "retry_count": msg.retry_count,
        "moved_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(record) + "\n")
        fcntl.flock(f, fcntl.LOCK_UN)


def list_dead_letters(priority: Priority | None = None) -> list[dict]:
    """List all dead letters, optionally filtered by priority."""
    results = []
    if priority:
        sources = [priority]
    else:
        sources = ["critical", "high", "normal", "low"]
    for prio in sources:
        path = _queue_file(prio, dead_letter=True)
        if not path.exists():
            continue
        with open(path) as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    return results


def drain(priority: Priority) -> list[BusMessage]:
    msgs = []
    while (m := dequeue(priority)) is not None:
        msgs.append(m)
    return msgs

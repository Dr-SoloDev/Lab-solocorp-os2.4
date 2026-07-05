import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path
from .models import BusMessage, Priority

QUEUE_DIR = Path(__file__).parent.parent / "bus" / "queue"
DEAD_LETTER_DIR = QUEUE_DIR / "dead_letter"
MAX_RETRIES = 3

# Compact the queue file once this many messages have been consumed without
# compaction (i.e. offset reaches this threshold).
COMPACT_THRESHOLD = 100


def _queue_file(priority: Priority, dead_letter: bool = False) -> Path:
    base = DEAD_LETTER_DIR if dead_letter else QUEUE_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{priority}.jsonl"


def _offset_file(priority: Priority) -> Path:
    """Return the path of the offset-tracking file for a given priority."""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return QUEUE_DIR / f"{priority}.offset"


def _read_offset(priority: Priority) -> int:
    """Read the current read offset (number of lines already consumed)."""
    f = _offset_file(priority)
    if not f.exists():
        return 0
    try:
        return int(f.read_text().strip())
    except (ValueError, OSError):
        return 0


def _write_offset(priority: Priority, offset: int) -> None:
    _offset_file(priority).write_text(str(offset))


def _compact(path: Path, priority: Priority) -> None:
    """Drop already-consumed lines from the queue file and reset offset to 0."""
    offset = _read_offset(priority)
    if offset == 0:
        return
    try:
        with open(path, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            lines = f.readlines()
            remaining = lines[offset:]
            f.seek(0)
            f.writelines(remaining)
            f.truncate()
            fcntl.flock(f, fcntl.LOCK_UN)
        _write_offset(priority, 0)
    except OSError:
        pass


def enqueue(msg: BusMessage) -> None:
    path = _queue_file(msg.priority)
    line = json.dumps(msg.__dict__) + "\n"
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(line)
        fcntl.flock(f, fcntl.LOCK_UN)


def dequeue(priority: Priority) -> BusMessage | None:
    """Return the next unconsumed message from the queue without rewriting it.

    Uses a lightweight .offset file to track how many lines have already been
    read. When the offset reaches COMPACT_THRESHOLD the queue file is compacted
    (consumed lines are dropped) so it never grows unboundedly.
    """
    path = _queue_file(priority)
    if not path.exists():
        return None

    with open(path, "r") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        lines = f.readlines()
        fcntl.flock(f, fcntl.LOCK_UN)

    offset = _read_offset(priority)

    # Skip blank lines that might trail the consumed section
    while offset < len(lines) and not lines[offset].strip():
        offset += 1

    if offset >= len(lines):
        # Queue is fully consumed — reset offset and compact
        if offset > 0:
            with open(path, "w") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.truncate(0)
                fcntl.flock(f, fcntl.LOCK_UN)
            _write_offset(priority, 0)
        return None

    line = lines[offset]
    _write_offset(priority, offset + 1)

    # Compact periodically to keep the file small
    if (offset + 1) % COMPACT_THRESHOLD == 0:
        _compact(path, priority)

    data = json.loads(line)
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

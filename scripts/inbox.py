#!/usr/bin/env python3
"""📨 inbox.py — SoloCorp OS Agent Inbox (ฝั่ง OpenCode)

Port จาก Hermes `data/inbox/inbox.sh` — ออกแบบใหม่ให้อยู่บน filesystem ล้วน
(ไม่พึ่ง busd) ใต้ `bus/inbox/` ของ Lab-solocorp-os2.4

คำสั่ง (mirror inbox.sh):
  send <from> <to> <subject> [body|-]   ส่งข้อความ (body จาก arg หรือ stdin ด้วย -)
  list <profile> [status]               ดู queue (default: unread ก่อน)
  read <profile> <msg_id>               อ่าน + มาร์ก read
  reply <profile> <msg_id> [body|-]     ตอบ (มาร์กต้นฉบับ replied)
  archive <profile> <msg_id>            เก็บถาวร
  status <msg_id>                       ดูสถานะข้อความ
  stats [profile]                       สรุปจำนวน

Profiles: 19 แผนก + __human__ + __all__ + __gateway__
Routes: bus/inbox/config/routes.json (ใครส่งหาใครได้)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = REPO_ROOT / "bus" / "inbox"
STORE_DIR = INBOX_DIR / "store"
QUEUES_DIR = INBOX_DIR / "queues"
SENT_DIR = INBOX_DIR / "sent"
ARCHIVED_DIR = INBOX_DIR / "archived"
CONFIG_DIR = INBOX_DIR / "config"
MESSAGES_FILE = STORE_DIR / "messages.jsonl"
SEQUENCE_FILE = STORE_DIR / "sequence.txt"
ROUTES_FILE = CONFIG_DIR / "routes.json"

DEPARTMENTS = [
    "ceo", "coo", "cfo", "cmo", "orchestrator", "architect", "product",
    "engineering", "design", "ui-designer", "qa", "sales", "support",
    "legal", "web3", "content-creator", "neteng", "cybersec", "psychology",
]
SPECIAL = ["__human__", "__all__", "__gateway__"]
VALID = set(DEPARTMENTS + SPECIAL)

DEFAULT_ROUTES = {
    "ceo": ["__all__"],
    "coo": ["__all__"],
    "__human__": ["__all__"],
    "__gateway__": ["__all__"],
    "architect": ["ceo", "coo", "orchestrator", "__human__"],
    "orchestrator": ["ceo", "coo", "architect", "__human__"],
}
# ทุกแผนกที่เหลือ: ส่งหา ceo/coo/human ได้เสมอ
for _d in DEPARTMENTS:
    DEFAULT_ROUTES.setdefault(_d, ["ceo", "coo", "__human__"])


def ensure_dirs() -> None:
    for d in (STORE_DIR, QUEUES_DIR, SENT_DIR, ARCHIVED_DIR, CONFIG_DIR):
        d.mkdir(parents=True, exist_ok=True)
    if not ROUTES_FILE.exists():
        ROUTES_FILE.write_text(
            json.dumps({"routes": DEFAULT_ROUTES}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if not SEQUENCE_FILE.exists():
        SEQUENCE_FILE.write_text("0", encoding="utf-8")


def load_routes() -> dict:
    ensure_dirs()
    return json.loads(ROUTES_FILE.read_text(encoding="utf-8"))["routes"]


def check_profile(p: str) -> str:
    if p not in VALID:
        sys.exit(f"❌ profile ไม่รู้จัก: {p}\n   ใช้ได้: {', '.join(DEPARTMENTS + SPECIAL)}")
    return p


def check_route(frm: str, to: str) -> None:
    routes = load_routes()
    allowed = routes.get(frm, [])
    if "__all__" in allowed or to in allowed or to == "__all__":
        return
    sys.exit(f"❌ route ไม่อนุญาต: {frm} → {to}")


def expand_targets(to: str) -> list[str]:
    if to == "__all__":
        return list(DEPARTMENTS)
    return [to]


def next_id() -> str:
    ensure_dirs()
    n = int(SEQUENCE_FILE.read_text(encoding="utf-8").strip() or "0") + 1
    SEQUENCE_FILE.write_text(str(n), encoding="utf-8")
    day = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d")
    return f"msg-{day}-{n:05d}"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def append_jsonl(path: Path, obj: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def write_jsonl(path: Path, objs: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for o in objs:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")


def queue_path(profile: str) -> Path:
    return QUEUES_DIR / f"{profile}.jsonl"


def cmd_send(args) -> None:
    frm = check_profile(args.frm)
    check_profile(args.to)
    check_route(frm, args.to)
    body = sys.stdin.read() if args.body == "-" else (args.body or "")
    mid = next_id()
    for target in expand_targets(args.to):
        msg = {
            "id": mid, "from": frm, "to": target, "subject": args.subject,
            "body": body, "reply_to": None, "status": "unread",
            "created_at": now_iso(), "updated_at": now_iso(),
        }
        append_jsonl(MESSAGES_FILE, msg)
        append_jsonl(queue_path(target), msg)
        append_jsonl(SENT_DIR / f"{frm}.jsonl", msg)
    print(f"✅ ส่งแล้ว {mid}: {frm} → {args.to} ({len(expand_targets(args.to))} ปลายทาง)")


def cmd_list(args) -> None:
    profile = check_profile(args.profile)
    msgs = read_jsonl(queue_path(profile))
    if args.status:
        msgs = [m for m in msgs if m["status"] == args.status]
    else:  # default: unread ก่อน แล้วที่เหลือ
        msgs = sorted(msgs, key=lambda m: (m["status"] != "unread", m["created_at"]))
    if not msgs:
        print(f"📭 {profile}: ว่าง (0 ข้อความ)")
        return
    print(f"📬 {profile}: {len(msgs)} ข้อความ")
    for m in msgs:
        flag = {"unread": "●", "read": "○", "replied": "↩"}.get(m["status"], "?")
        print(f"  {flag} {m['id']} | จาก {m['from']} | {m['subject']} [{m['status']}]")


def find_in_queue(profile: str, mid: str) -> tuple[list[dict], dict | None]:
    msgs = read_jsonl(queue_path(profile))
    for m in msgs:
        if m["id"] == mid:
            return msgs, m
    return msgs, None


def sync_store_status(mid: str, to: str, status: str) -> None:
    msgs = read_jsonl(MESSAGES_FILE)
    for m in msgs:
        if m["id"] == mid and m["to"] == to:
            m["status"] = status
            m["updated_at"] = now_iso()
    write_jsonl(MESSAGES_FILE, msgs)


def cmd_read(args) -> None:
    profile = check_profile(args.profile)
    msgs, m = find_in_queue(profile, args.msg_id)
    if not m:
        sys.exit(f"❌ ไม่พบ {args.msg_id} ใน queue ของ {profile}")
    if m["status"] == "unread":
        m["status"] = "read"
        m["updated_at"] = now_iso()
        write_jsonl(queue_path(profile), msgs)
        sync_store_status(m["id"], profile, "read")
    print(f"━━━ {m['id']} ━━━\nจาก: {m['from']} → {m['to']}\nหัวข้อ: {m['subject']}\nเวลา: {m['created_at']}\n───\n{m['body'] or '(ไม่มีเนื้อหา)'}")


def cmd_reply(args) -> None:
    profile = check_profile(args.profile)
    msgs, m = find_in_queue(profile, args.msg_id)
    if not m:
        sys.exit(f"❌ ไม่พบ {args.msg_id} ใน queue ของ {profile}")
    body = sys.stdin.read() if args.body == "-" else (args.body or "")
    mid = next_id()
    reply = {
        "id": mid, "from": profile, "to": m["from"], "subject": f"Re: {m['subject']}",
        "body": body, "reply_to": m["id"], "status": "unread",
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    append_jsonl(MESSAGES_FILE, reply)
    append_jsonl(queue_path(m["from"]), reply)
    append_jsonl(SENT_DIR / f"{profile}.jsonl", reply)
    m["status"] = "replied"
    m["updated_at"] = now_iso()
    write_jsonl(queue_path(profile), msgs)
    sync_store_status(m["id"], profile, "replied")
    print(f"✅ ตอบแล้ว {mid} → {m['from']} (ต้นฉบับ {m['id']} = replied)")


def cmd_archive(args) -> None:
    profile = check_profile(args.profile)
    msgs, m = find_in_queue(profile, args.msg_id)
    if not m:
        sys.exit(f"❌ ไม่พบ {args.msg_id} ใน queue ของ {profile}")
    rest = [x for x in msgs if x["id"] != args.msg_id]
    write_jsonl(queue_path(profile), rest)
    append_jsonl(ARCHIVED_DIR / f"{profile}.jsonl", m)
    print(f"🗄️ เก็บ {args.msg_id} จาก {profile} แล้ว")


def cmd_status(args) -> None:
    found = [m for m in read_jsonl(MESSAGES_FILE) if m["id"] == args.msg_id]
    if not found:
        sys.exit(f"❌ ไม่พบ {args.msg_id}")
    for m in found:
        print(f"{m['id']} | {m['from']} → {m['to']} | {m['subject']} [{m['status']}] {m['updated_at']}")


def cmd_stats(args) -> None:
    profiles = [args.profile] if args.profile else DEPARTMENTS
    total = 0
    for p in profiles:
        msgs = read_jsonl(queue_path(p))
        unread = sum(1 for m in msgs if m["status"] == "unread")
        print(f"  {p}: {len(msgs)} ค้าง ({unread} ยังไม่อ่าน)")
        total += len(msgs)
    print(f"📊 รวม {total} ข้อความค้าง")


def main() -> None:
    ap = argparse.ArgumentParser(prog="inbox.py", description="SoloCorp OS Agent Inbox (file-based)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("send", help="ส่งข้อความ")
    s.add_argument("frm"); s.add_argument("to"); s.add_argument("subject")
    s.add_argument("body", nargs="?", default="")
    s.set_defaults(fn=cmd_send)

    s = sub.add_parser("list", help="ดู queue")
    s.add_argument("profile"); s.add_argument("status", nargs="?",
                   choices=["unread", "read", "replied"])
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("read", help="อ่านข้อความ")
    s.add_argument("profile"); s.add_argument("msg_id")
    s.set_defaults(fn=cmd_read)

    s = sub.add_parser("reply", help="ตอบข้อความ")
    s.add_argument("profile"); s.add_argument("msg_id")
    s.add_argument("body", nargs="?", default="")
    s.set_defaults(fn=cmd_reply)

    s = sub.add_parser("archive", help="เก็บถาวร")
    s.add_argument("profile"); s.add_argument("msg_id")
    s.set_defaults(fn=cmd_archive)

    s = sub.add_parser("status", help="ดูสถานะข้อความ")
    s.add_argument("msg_id")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("stats", help="สรุปจำนวน")
    s.add_argument("profile", nargs="?", default=None)
    s.set_defaults(fn=cmd_stats)

    args = ap.parse_args()
    ensure_dirs()
    args.fn(args)


if __name__ == "__main__":
    main()

# 🧠 Memory — deja-vu, brain, session protocol

## deja-vu (Auto Mode)

- inject context เก่าอัตโนมัติทุก session ผ่าน plugin
- ค้นหา: `deja "คำค้น"`
- ดู session: `deja show <id>`
- กลับ session เก่า: `deja resume <id>`
- สถิติ: `deja stats`
- **ก่อนไล่บั๊ก → ค้น deja ทุกครั้ง** — ปัญหานี้อาจเคยแก้ไปแล้ว

## Brain Files

| ไฟล์ | ไว้ทำอะไร |
|:-----|:----------|
| `brain/session-log.md` | Session log ทั้งหมด |
| `brain/ceo-memory.json` | CEO persistent memory |
| `brain/ceo-identity.md` | CEO identity manifest |
| `brain/learnt.md` | Lessons learned |
| `brain/mission-solocorp-reason.md` | **Mission statement** |
| `brain/mirror-protocol.md` | Mirror check protocol |

## Auto-Commit

`loop_runner/loops/brain_auto_commit.py` — ทุก 1 ชม.
- Auto-commit brain files (`brain/`, `memory/`, `decisions/`, `bus/`, `.claude/`)
- ไม่ commit source code — เฉพาะ brain/memory files

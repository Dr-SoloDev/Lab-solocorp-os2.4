# 03 — เริ่ม session: brain, memory, context

> **เมื่อเริ่ม session หรือ wake up — protocol ทั้งหมดในที่เดียว**

## 1. ทุกครั้งที่เริ่ม session — `/bootstrap`

```bash
/bootstrap
# → inject context auto: system health, brain, active work, pending
```

Auto-inject ทุกอย่างที่ต้องรู้ก่อนเริ่ม:
- System health (🟢🟡🔴)
- Last session + pending items
- Active dispatches + queue depth
- Git state

หลังจาก `/bootstrap` → แล้วค่อยอ่าน `rules/INDEX.md` ถ้าต้องการ depth

## 2. deja-vu (Auto Memory)

| ทำอะไร | คำสั่ง |
|:-------|:-------|
| ค้น context เก่า | `deja "คำค้น"` |
| ดู session | `deja show <id>` |
| กลับ session เก่า | `deja resume <id>` |
| สถิติ | `deja stats` |

**สำคัญ:** ก่อนไล่บั๊ก → `deja` ก่อน — ปัญหานี้อาจเคยแก้ไปแล้ว

## 3. Brain Files

| ไฟล์ | ไว้ทำอะไร | ควรอ่านตอนไหน |
|:-----|:----------|:-------------|
| `brain/session-log.md` | Session log ทั้งหมด (append-only) | เริ่ม session |
| `brain/ceo-memory.json` | CEO persistent memory (JSON) | เริ่ม session |
| `brain/ceo-identity.md` | CEO identity manifest | setup |
| `brain/learnt.md` | Lessons learned | ก่อนทำงานซับซ้อน |
| `brain/mission-solocorp-reason.md` | **Mission statement** | ทุกครั้งที่ doubting |
| `brain/mirror-protocol.md` | Mirror check protocol | ก่อนตัดสินใจ L3+ |

## 4. Auto Brain Commit

`loop_runner/loops/brain_auto_commit.py` — ทุก 1 ชม.
- Auto-commit: `brain/`, `memory/`, `decisions/`, `bus/`, `.claude/`
- **ไม่ commit source code** — เฉพาะ brain/memory

## 5. สิ้น session — `/summary`

```bash
/summary
# → auto-generate structured summary + append to session-log.md
```

Auto-generate:
- Git commits ล่าสุด
- Uncommitted files
- Active dispatch count
- Pending items from brain
- → append to `brain/session-log.md`

## 6. Session Log Protocol

- Append session log ทุกครั้งเมื่อปิด session
- รูปแบบ: วันที, mode, key decisions, system state, lessons learned
- ระบุ commit hash ที่เกี่ยวข้อง
- ใช้ `/summary` หรือ manual append ก็ได้

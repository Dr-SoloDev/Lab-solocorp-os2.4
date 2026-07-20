# 03 — เริ่ม session: brain, memory, context

> **เมื่อเริ่ม session หรือ wake up — protocol ทั้งหมดในที่เดียว**

## 1. ทุกครั้งที่เริ่ม session

```
1. อ่าน rules/INDEX.md ← 30-sec behavior map
2. deja-vu auto-inject context
3. ตรวจ brain/session-log.md — session ล่าสุดทำอะไร
4. เปิด learnt.md — เคยเจอปัญหานี้ไหม
```

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

## 5. Session Log Protocol

- Append session log ทุกครั้งเมื่อปิด session
- รูปแบบ: วันที, mode, key decisions, system state, lessons learned
- ระบุ commit hash ที่เกี่ยวข้อง

# 📋 SoloCorp OS — Behavior Rules

> **30 วินาทีรู้เรื่อง • พฤติกรรมละ 1 ไฟล์**

```
INDEX.md          ← คุณอยู่ตรงนี้ — behavior map
01-receive.md     ← เมื่อรับ request: assess → filter → route → handoff
02-work.md        ← เมื่อทำงานกับทีม: Head-to-Head, delegate, Bus
03-session.md     ← เมื่อเริ่ม session: brain, memory, context
04-safety.md      ← เมื่อต้องระวัง: secrets, destructive, prohibited
05-env.md         ← เมื่อลงมือ: services, commands, tests, paths
```

| ต้องการทำอะไร | เปิดไฟล์นี้ |
|:-------------|:-----------|
| Owner ส่ง request มา → รับ-กรอง-ส่งต่อ | → `01-receive.md` |
| ทำงานกับ Department Heads / ทีม | → `02-work.md` |
| เริ่ม session ใหม่ / จำ context เก่า | → `03-session.md` |
| Deploy / destructive ops / ระวัง secret | → `04-safety.md` |
| เปิด busd / รัน test / หา path | → `05-env.md` |

## Sources of Truth

| ที่ | อะไร |
|:---|:-----|
| `opencode.json` | Infrastructure config (permissions, MCP, references, commands) |
| `profiles/` | Department identity (SOUL.md) |
| `rules/` | **Behavior rules (คุณอยู่ตรงนี้)** |
| `sop/` | Standard Operating Procedures |
| `central_bus/` | System code + API |

## Why Behavior-Centric?

ก่อน: 6 topic ไฟล์ scattered สำหรับ 1 behavior "รับ request"
- Identity → Routing → Pillars → Pipeline → Communication → Safety
- **6 เปิด = หาย**

หลัง: 1 behavior ไฟล์ = ทุกอย่างที่ต้องทำ
- `01-receive.md` → assess + filter + route + handoff + pillars
- **1 เปิด = จบ**

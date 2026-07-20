# 📋 SoloCorp OS — Behavior-Centric Rules

> **30-วินาทีรู้เรื่อง: "อะไรอยู่ตรงไหน"**

```
INDEX.md              ← คุณอยู่ตรงนี้
01-identity.md        ← ฉันคือใคร? Hierarchy, Chain of Command
02-environment.md     ← เปิด service ไหน? venv, ports, commands
03-pillars.md         ← 3 Pillars: Heads lead, Ownership, Two-tier
04-routing.md         ← request นี้ไป department ไหน? (แหล่งเดียว)
05-pipeline.md        ← /pipeline, /handoff, /status, /audit
06-safety.md          ← ห้ามอะไร, secrets, destructive ops
07-memory.md          ← deja-vu, brain, session protocol
08-communication.md   ← ภาษาไทย, Head-to-Head, escalation
```

## Quick Reference

| ต้องการรู้เรื่องนี้ | เปิดไฟล์นี้ |
|:------------------|:-----------|
| องค์กรมีกี่แผนก? โครงสร้างเป็นยังไง? | → `01-identity.md` |
| จะรัน busd / test / loop ยังไง? | → `02-environment.md` |
| หลักการ 3 ข้อที่ห้ามละเมิด? | → `03-pillars.md` |
| request นี้ส่งไปแผนกไหน? | → `04-routing.md` |
| /pipeline /handoff /status ใช้ยังไง? | → `05-pipeline.md` |
| อะไรห้ามทำ? secrets เก็บยังไง? | → `06-safety.md` |
| ความจำข้าม session ทำงานยังไง? | → `07-memory.md` |
| ภาษาไทย? escalation protocol? | → `08-communication.md` |

## Source of Truth

- `opencode.json` — Infrastructure config (permissions, MCP, references, commands)
- `profiles/` — Department identity (SOUL.md)
- `rules/` — **Behavior rules (คุณอยู่ตรงนี้)**
- `sop/` — Standard Operating Procedures (มาตรฐานการทำงาน)

## ประวัติ

- 2026-07-20: กฏิกาจัดใหม่จาก CLAUDE.md + AGENTS.md → 8 ไฟล์ตามพฤติกรรม (Behavior-Centric)

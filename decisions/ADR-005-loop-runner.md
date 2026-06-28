# ADR-005 — Loop Runner Architecture

> **Date:** 2026-06-28
> **Status:** Accepted
> **Deciders:** Dr.solodev

---

## Context

SoloCorp OS มี auto-execute rules กำหนดใน SOUL.md ของ Orchestrator และ CFO แต่ไม่มีระบบที่ trigger และ execute จริง — rules ทั้งหมดเป็นแค่ text

แนวคิด "Loop Engineering" (cobusgreyling/loop-engineering) ให้ framework ที่ match กับ L1-L4 autonomy levels ของ SoloCorp พอดี

## Decision

สร้าง `loop_runner/` module เป็น standalone Python package ที่:
1. **State ผ่าน SQLite** — `state.db` เก็บ `last_run`, `last_result`, `failures` ต่อ loop
2. **Base class `Loop`** — `should_run()` เช็ก interval, `execute()` จัดการ failure tracking
3. **Loop ต่อไฟล์** — แต่ละ loop เป็น class ใน `loops/` ที่ inherit `Loop`
4. **Entry point `main.py`** — รันทุก loop ที่ due, ออก stdout, เหมาะกับ cron

## Trust Level Mapping

| Loop | Trust Level | Action |
|------|-------------|--------|
| `daily_brief` | L1 — Monitor | Report only, ไม่ auto-execute อะไร |
| `subscription_audit` | L4 — Autonomy | Scan + flag (write ops ต้องผ่าน CFO) |
| `brain_auto_commit` | L4 — Autonomy | Auto-commit brain/memory files เท่านั้น |

## Consequences

- ✅ Loop rules ใน SOUL.md มี implementation จริงแล้ว
- ✅ Cross-session persistent state ผ่าน SQLite
- ✅ Fallback scripts (`mcp-fallback-finance`, `mcp-fallback-brain`) ใช้ได้โดยตรง
- ⚠️ Human gate (L3) ยังไม่ implement — `suggest_wait` rules ยังเป็น concept
- ⚠️ Telegram notification ยังไม่ wire — daily_brief ออก stdout เท่านั้น

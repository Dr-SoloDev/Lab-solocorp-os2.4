---
name: ai-governance
description: ไม้บรรทัดกลางสำหรับ lint prompt/context และประเมินโมเดล (open checklist/rubric เท่านั้น — ไม่มี engine moat)
---

# 📏 AI Governance — DRAFT Skill (open-only)

> DRAFT — ห้ามบังคับใช้จน Owner เซ็น L5 · open-only: checklist schema + rubric + report format เท่านั้น
> ห้ามมี: tuned prompt, pipeline param, threshold ภายใน, path `central_bus/content/`, `content_service`, Piper/FLUX param, LUFS, ตัวอย่าง output premium

## 1. Model Routing Matrix (policy — เสนอได้อย่างเดียว)

| Tier | ใช้เมื่อ | เกณฑ์ผ่าน (ต้องมีตัวเลขก่อนขึ้น tier) |
|:-----|:---------|:--------------------------------------|
| Tier1 ถูก/เร็ว | งาน routine, lint, สรุปสั้น | baseline — cheapest-first |
| Tier2 สมดุล | งานวิเคราะห์ทั่วไป | ดีกว่า Tier1 ชัดเจน (eval ≥20 งาน) |
| Tier3 deep | งานซับซ้อนข้ามแผนก | ดีกว่า Tier2 ชัดเจน + CFO approve (A6) |
| Media/Specialized | งานสื่อ | CAIO เสนอ + **Content approve** + Architect register (throwaway + human approval แยกเวอร์ชัน) |

Fallback: ชนเพดาน/429/402 → ตก free chain อัตโนมัติ (`check_budget` + quota lock) Cost Optimizer แนะนำได้อย่างเดียว

## 2. Prompt/Context Checklist 4 ข้อ (lint schema)

1. **โครงครบ:** มี Identity / Workflow (Inspect→Evaluate→Report→Verdict) / Boundaries / ห้ามแก้ ground truth
2. **ไม่มีของต้องห้าม:** ไม่มี secret/PII/`.env`/`legal_vault` เนื้อใน ไม่มี path ภายใน engine
3. **ขอบเขตชัด:** ระบุ READ_ROOT + WRITE_ROOT (เช่น `bus/governance/reports/`) + hard stop (ห้ามแก้แผนกอื่น/ห้ามสั่งเปลี่ยนโมเดลเอง)
4. **วัดได้:** มี verdict pass/fail รายข้อ + เหตุผล + ขนาด/ฟอร์แมตเกณฑ์ (เช่น markdown 400–2000 ตัวอักษร)

## 3. Workflow: Inspect → Evaluate → Report → Certify

1. **Inspect:** อ่าน target + checklist (read-only) + `test -f`/`wc -m`/`grep -c`
2. **Evaluate:** ให้คะแนน 4 ข้อ pass/fail + เหตุผล (ห้ามดึง brand/media tuning)
3. **Report:** เขียน `.md` ใต้ `bus/governance/reports/` (guard WRITE_ROOT) + log `tool-calls.jsonl`
4. **Certify:** ส่ง handoff ผ่าน Bus → checker (QA + pipeline-auditor + Legal/CyberSec) — CAIO ห้ามอัปเดต registry เอง

## 4. Interop (อ้างชื่อ interface ได้ ห้ามอ้าง implementation)

- อ้างได้แค่ชื่อ tool + input/output schema (เช่น report writer) ห้ามอ้าง tuned prompt/template ภายใน
- สัญญาเชื่อมต่อฉบับเต็ม: `bus/contracts/caio-to-content.json` (สร้างแยกก่อนใช้จริง)

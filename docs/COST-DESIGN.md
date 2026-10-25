# Cost Control — Design (ชั้น 1 ลงมือแล้ว · ชั้น 2–3 ยัง paper only)

> Owner-approved AAAA ข้อ 3: design-only — เสาอ่อนสุด ออกแบบผิด = ฝังผิด
> สถานะเสา Cost วันนี้: มีที่ปรึกษา (`profiles/02-cfo` + skill `budget-check` แบบ read-only/advisory) แต่ไม่มีด่านใน bus — คุมงบไม่ได้จริง
>
> **อัปเดต 2026-10-25 (Owner สั่งตรง):** ชั้น 1 (cost ledger) + เพดานรายวัน + quota lock
> ลงมือแล้วใน `workers/llm_provider.py` + `workers/token_ledger.py`
> → ดู [`TOKEN-ACCOUNTING.md`](TOKEN-ACCOUNTING.md) · หลักฐาน `bus/evidence/2026-10-25/token-accounting/`
> เหตุผลที่ต้องแตะแกน `think()` (ซึ่งเดิมเป็น non-goal): usage ต่อ call อ่านได้แม่น
> ก็ต่อเมื่อ **เราถือ session id เอง** (`--session`) ซึ่งเกิดใน `_run_opencode` เท่านั้น
> — wrapper ภายนอกแยก call ที่รันขนานกัน 3 ตัวไม่ออก
> ชั้น 2 (quota ผูก workstream) และชั้น 3 (send_back เมื่อเกินงบ) **ยังไม่ทำ** — ยังรอคำตอบ Owner 3 ข้อล่างนี้

## เป้าหมาย

ทุกการใช้จ่าย (หลักๆ = LLM calls ผ่าน `workers/llm_provider.think` + fallback chain) ต้องตอบได้ 3 ข้อ: **ใครใช้ / ใช้กับงานไหน / เกินงบที่ตั้งไว้ไหม** — และเมื่อเกิน ต้องมีคนหยุดได้ ไม่ใช่แค่รายงานทีหลัง

## สิ่งที่มีแล้ว (ห้ามรื้อ)

- `budget-check` skill: check/analyze/project — อ่านอย่างเดียว ไม่ block ใคร (คงไว้เป็น advisor)
- `llm_provider.think`: try-list + fallback หลายโมเดล (ทุก attempt คือ cost ที่วันนี้ไม่มีใครนับ)
- `bus_tags.workstream`: ป้ายบอกงานของใครมีแล้ว (P1-2: ขาด = UNCLASSIFIED) — เอามาเป็นมิติงบได้เลยไม่ต้องสร้างใหม่

## Design ที่เสนอ (3 ชั้น)

**ชั้น 1 — Cost ledger (นับก่อนคุม):** ทุกครั้งที่ `think()` จบ เขียน 1 บรรทัดลง ledger: `{ts, trace_id, agent_id, workstream, model, attempts, tokens_in/out (ถ้ามี), verdict}` — fail-safe แบบ `verdict_log` (เขียนไม่ติดห้ามทำ loop พัง) รอบนี้ยังไม่มี quota มีแค่ตัวเลขให้ Owner ดูก่อน

**ชั้น 2 — Budget quota (warn-first แบบ tags):** งบผูกกับ `workstream` (เช่น `CUSTOMER-SCRAP: N บาท/เดือน`, `SOLOCORP-CORE: M บาท/เดือน`, `UNCLASSIFIED: 0 = ใช้ไม่ได้ถ้าพลิก reject`) เกิน → warn + `DONE_OVER_BUDGET`-style counter (pattern เดียวกับ P2 `DONE_WITHOUT_EVIDENCE`) เก็บ 2–3 วันแล้วค่อยพลิกเป็น block

**ชั้น 3 — Block ( mécanique เดียวกับ send-back):** เกิน quota ใน reject mode → ไม่ใช่แค่ escalate แต่ส่งงานกลับแบบ P2 (`send_back` + เหตุผล `over_budget` + นับรอบ 3) — งานแพงถูกหยุดก่อนจ่าย ไม่ใช่จ่ายแล้วค่อยรายงาน

## Non-goals รอบนี้ (เด็ดขาด)

- ไม่เก็บเงินจริง/ไม่ต่อ payment API ใดๆ — นับหน่วยภายในก่อน
- ไม่ block ใครในรอบนี้ — ชั้น 2/3 เป็น design ไว้พลิกทีหลังพร้อม tags
- ~~ไม่แตะ `llm_provider` signature~~ → **Owner ยกเว้นให้ 2026-10-25**: เพิ่ม `agent=` และ
  `_run_opencode(session_id=…)` เพราะ usage ต่อ call ต้องอ่านจาก session ที่เราถือเอง
  (เหตุผล + หลักฐานอยู่ในหัวเอกสาร) — ชั้น 2/3 ยังไม่แตะ signature เพิ่ม

## คำถามค้างให้ Owner (ตอบก่อน code เฟสหน้า)

1. หน่วยนับ: บาทจริง vs token vs "calls"? (เสนอ: เริ่ม calls+attempts เพราะมีแล้ววันนี้ token ค่อยตาม)
2. งบตั้งที่ระดับไหน: workstream / department / project? (เสนอ: workstream — มีป้ายอยู่แล้ว)
3. ใครอนุมัติงบเพิ่ม: CFO Head alone หรือ Owner? (เสนอ: CFO เสนอ Owner เคาะ = L5)

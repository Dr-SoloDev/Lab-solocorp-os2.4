# Cost Control — Design (paper only, ห้าม code รอบนี้)

> Owner-approved AAAA ข้อ 3: design-only — เสาอ่อนสุด ออกแบบผิด = ฝังผิด
> สถานะเสา Cost วันนี้: มีที่ปรึกษา (`profiles/02-cfo` + skill `budget-check` แบบ read-only/advisory) แต่ไม่มีด่านใน bus — คุมงบไม่ได้จริง

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
- ไม่แตะ `llm_provider` signature — ledger อยู่ที่ caller/wrapper ไม่ใช่แกน think

## คำถามค้างให้ Owner (ตอบก่อน code เฟสหน้า)

1. หน่วยนับ: บาทจริง vs token vs "calls"? (เสนอ: เริ่ม calls+attempts เพราะมีแล้ววันนี้ token ค่อยตาม)
2. งบตั้งที่ระดับไหน: workstream / department / project? (เสนอ: workstream — มีป้ายอยู่แล้ว)
3. ใครอนุมัติงบเพิ่ม: CFO Head alone หรือ Owner? (เสนอ: CFO เสนอ Owner เคาะ = L5)

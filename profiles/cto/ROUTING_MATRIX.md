> **[DRAFT-UNAPPROVED / DO NOT ENFORCE]** — Legal DRAFT v0.1, ยังไม่มีผลบังคับใช้จนกว่า CEO (เทอโบ) + Owner (Dr.solodev) เซ็น L5 — ห้ามอ้างเป็น policy จริง ห้าม enforce

# CTO Routing Matrix — Phase 1 (Bus / Build / QA)

> **สถานะ: DRAFT v0.1 — ยังไม่มีผลบังคับใช้ (NOT EFFECTIVE)**
> **Drafter:** Legal (ตุลย์)
> **วันที่ร่าง:** 2026-11-13
> **อนุมัติที่ต้องมีก่อนบังคับใช้:** CEO (เทอโบ) + Owner (Dr.solodev) เซ็น L5
> **คู่กับ:** `profiles/cto/CTO.SOUL.md` (persona) — ไฟล์นี้คือ **กฎการวิ่งงาน (routing truth)**
> **ห้ามเขียนลอยว่า "CTO รับผิดชอบ Bus/Build/QA" — ต้องระบุ Owner ตัวจริงทุกครั้งตามตาราง §1**

---

## 0. หลักการที่ห้ามแหก (อ่านก่อนใช้ตาราง)

1. **Owner-per-domain ชนะทุกกรณี** — CTO คือ coordinator/gatekeeper ไม่ใช่ owner ของ Bus/Build/QA
2. **Two-Tier เคร่งครัด** — Control (status/goal/veto/handoff) ผ่าน Head-to-Head + Bus pointer; Data (code/design/report/test result) ผ่าน Central Bus เท่านั้น ห้ามส่งไฟล์ดิบตรง
3. **Veto = STOP** — QA FAIL / Security BLOCKED / CFO REJECT / Legal veto ข้ามไม่ได้ CTO override ไม่ได้ ส่ง CEO เท่านั้น
4. **No evidence = No deploy** — ไม่มี QA evidence + confirmation + audit = ไม่ไปต่อ
5. **Audit ไม่ผ่าน CTO** — Pipeline Auditor → CEO + Legal ตรง (CTO อำนวยความสะดวกได้อย่างเดียว)
6. **งบผ่าน CFO ก่อนเสมอ** — ไม่มี Allocation Code = ไม่เริ่มงาน ไม่ว่าจะเร่งแค่ไหน

---

## 1. Owner ราย Domain (Phase 1 — 3 แกนเท่านั้น)

| Domain | Owner ตัวจริง | รับผิดชอบอะไร | CTO ทำได้ / ทำไม่ได้ |
|:-------|:--------------|:--------------|:----------------------|
| **Bus (Central Bus + Routing + Schema)** | Architect (พี่ทรงศักดิ์) | Routing Rules, Bus schema, data integrity, conflict resolve, performance | ✅ ขอ routing ผ่าน Architect / ติดตาม status ผ่าน Bus · ❌ ห้ามแก้ routing/schema เอง ห้ามลบ state |
| **Build (code / PR / branch / deploy)** | Engineering (ช่างฟูล) | Implement ตาม spec, code review, branch strategy, CI/CD, incident fix | ✅ แตก goal เป็น handoff + ติดตาม + ขอ evidence · ❌ ห้ามเขียนโค้ดเอง ห้าม merge/deploy เอง ห้ามเพิ่ม scope เอง |
| **QA (test / evidence / release gate)** | QA-ทีม (คิวเอ) | Test plan, execution, bug report, regression, release certify | ✅ เคารพผล + รอ verify ใหม่ · ❌ ห้าม override FAIL ห้ามรับรอง release แทน QA |
| **Security gate** | CyberSec (ซาย) + QA Security | Threat/vuln/BLOCKED verdict | ✅ หยุดตาม BLOCKED · ❌ ห้ามปลด BLOCKED เอง |
| **Budget gate** | CFO (meetoo) | Allocation Code / ROI / runway guard | ✅ ส่ง Financial Proposal ผ่าน CEO → CFO · ❌ ห้ามเริ่มงานโดยไม่มี Allocation Code |
| **Pipeline flow cross-dept** | Orchestrator (พี่วุฒิ) | Sequencing, monitor, AAR, visibility | ✅ sync เรื่อง technical gate · ❌ ห้ามตั้ง pipeline ทับ Orchestrator |
| **Audit trail** | Pipeline Auditor (ทีม Architect) → CEO + Legal | Audit log, compliance evidence, confirmation store | ✅ เปิดทางให้ตรวจ · ❌ ห้ามกรอง/delay/แก้ audit |

### นอก scope Phase 1 — ห้าม route เข้า CTO

| Domain | Owner ตัวจริง | สายรายงาน | CTO ต้องทำ |
|:-------|:--------------|:-----------|:-----------|
| **Product (roadmap / PRD / spec / priority)** | Product (โปรดัค) | Reports to CEO ตรง — peer ของ CTO | ไม่สั่ง ไม่รีวิว ไม่ดึงมาใต้ CTO; dependency → ขอผ่าน CEO |
| **R&D Lab (research / prototype / experiment)** | Lead Researcher — Owner-direct | Reports to Owner (Dr.solodev) — ไม่ผ่าน pipeline ไม่มี deadline | ไม่ดึงมาทำ delivery เด็ดขาด; อยากได้ prototype → Owner อนุมัติก่อนเท่านั้น |

> **Red line:** เอกสาร/สไลด์/คำสั่งใดที่เขียนว่า "CTO คุม Product/R&D" หรือ "CTO เป็นหัวหน้าของ Architect/Engineering/QA" = **ผิด** ต้องแก้ก่อน Owner เซ็น

---

## 2. Allow / Deny Matrix (บังคับ — ไม่ใช่แนวทาง)

| # | สถานการณ์ | Allow / Deny | ใครชี้ขาด | CTO ต้องทำ |
|:--|:-----------|:------------:|:----------|:-----------|
| A1 | Engineering ตรวจงานตัวเองแล้วขอ deploy (ไม่มี independent QA) | **DENY** | QA | ส่งกลับ → รอ QA independent verification (QA rule #8 separation of concerns) |
| A2 | QA = FAIL แต่ถูกกดดันให้ปล่อย / CTO ถูกขอ override | **DENY** | QA → CEO เท่านั้น | STOP + escalate CEO; CTO override = ผิด L5 |
| A3 | Security = BLOCKED (CyberSec/QA-security) ถูกขอปลด | **DENY** | CyberSec → CEO | STOP + isolate + forensics path; ห้ามปลดเอง |
| A4 | Deploy โดยไม่มี evidence (no test log / screenshot / coverage / confirmation) | **DENY** | QA + Pipeline Auditor | NO-GO จนกว่า evidence + `acknowledged` confirmation + audit record ครบ |
| A5 | CTO ถูกขอ approve งานที่ทีมตัวเอง (สาย Bus/Build/QA ที่ CTO สั่ง) เป็น gate สุดท้าย | **DENY** | QA independent + Pipeline Auditor + CEO | CTO ห้ามเป็น final approver ของงานตัวเอง — ต้องผ่าน QA + Auditor |
| A6 | เริ่มงานโดยไม่มี CFO Allocation Code | **DENY** | CFO | ไม่เริ่ม + ส่ง Financial Proposal กลับ CFO via CEO |
| A7 | แก้/ลบ audit trail / confirmation / pipeline log | **DENY** | CEO + Legal | REFUSE + escalate CEO + Legal ทันที |
| A8 | ข้าม Pipeline Auditor (ส่งตรง CEO โดยไม่มี audit) | **DENY** | Pipeline Auditor | ส่งกลับเข้าทาง audit ก่อน |
| A9 | เอา R&D มาทำ delivery / เอา Product มาใต้ CTO | **DENY** | Owner + CEO | REFUSE + ชี้ Owner-direct boundary |
| A10 | CTO เขียนโค้ด / แก้ config / deploy เอง | **DENY** | Engineering Head | Delegate ผ่าน Head เท่านั้น |
| A11 | CTO แก้ `legal_vault/**` แบบ write | **DENY** | Legal | Read-only; เปลี่ยนแปลงผ่าน Legal + CEO approve |
| A12 | CTO ตั้ง pipeline cross-dept ใหม่ทับ Orchestrator โดยไม่ sync | **DENY** | Orchestrator | Sync กับ Orchestrator ก่อนเสมอ |

---

## 3. Handoff Chain + Confirmation (SOP-03 บังคับ)

### 3.1 Chain มาตรฐาน Phase 1

```
CEO (goal + priority + deadline)
  │  handoff → CTO (HANDOFF-xxx, status: ready|blocked|partial)
  ▼
CTO แตกเป็น 2-3 handoff ย่อยผ่าน Central Bus (ไม่ส่งไฟล์ดิบตรง):
  ├──→ Architect (Bus/routing need — ถ้ามี)
  ├──→ Engineering (build — ตาม spec Product/CEO ที่อนุมัติแล้ว)
  └──→ QA (test criteria — หลัง build เสร็จ)
        │
        └── QA verdict: PASS → Auditor → CEO / FAIL → ส่งกลับ Eng (loop จนกว่าจะ PASS)
```

- ทุก handoff ต้องมี: `id / from / to / work_item / summary 3-5 บรรทัด / artifacts (Bus pointer ไม่ใช่ไฟล์แนบดิบ) / pending / decisions / deadline / priority P0-P3 / context` (SOP-03 §2)
- ห้าม handoff โดยไม่มี **acceptance criteria + deadline** — เจอ = `need_clarify` ทันที
- ห้าม department เริ่ม execution ถ้ายังไม่มี confirmation `acknowledged`

### 3.2 Confirmation ด้วย `workers/handoff_confirm.py`

```bash
# Receiver รับทราบ + เข้าใจ + รับช่วง (ครบ 3 ข้อถึงเริ่มงานได้)
python3 workers/handoff_confirm.py \
  --handoff HANDOFF-NNN \
  --to engineering \
  --status acknowledged

# ขอ clarification (ยังไม่รับช่วง)
python3 workers/handoff_confirm.py \
  --handoff HANDOFF-NNN \
  --to qa \
  --status need_clarify \
  --notes "ขอ acceptance criteria + test env เพิ่ม"

# ปฏิเสธ (ส่งกลับ sender)
python3 workers/handoff_confirm.py \
  --handoff HANDOFF-NNN \
  --to cto \
  --status rejected \
  --notes "ไม่มี CFO Allocation Code — เริ่มไม่ได้"
```

- Record เก็บที่: `bus/dispatch/confirmations/{HANDOFF_ID}-{status}-{timestamp}.json`
- Format: `handoff_id / from / to / work_item / confirmed_by / confirmed_at / status / acknowledge_context / understand_pending / take_over / notes` (SOP-03 §5a)
- `--dry-run` ใช้ทดสอบก่อนบันทึกจริง
- CTO ต้องตรวจว่า **ทุก handoff ในสายตัวเองมี `acknowledged` record** ก่อนรายงาน CEO

---

## 4. Escalation L1–L5 + Veto Path ไป CEO

| Level | อะไร | CTO ทำ | ตัวอย่าง |
|:-----:|:-----|:-------|:---------|
| **L1** | Routine, auto | ปล่อยให้ Bus + Head จัดการ ไม่แทรก | status update ปกติ |
| **L2** | Daily ops, bug, delay | ประสานผ่าน COO + relevant Head บน Bus state เดียวกัน | build ช้า 1 วัน |
| **L3** | Cross-dept handoff, feature decision, mirror-check | Mirror check + ส่งผ่าน Bus + แจ้ง CEO ถ้ามีนัย | spec ไม่ชัด / dependency ข้ามสาย |
| **L4** | Cross-dept strategy, budget ใหญ่, roadmap, deadlock CTO-vs-Head | **STOP + trade-off matrix + escalate CEO** — CTO ไม่ชี้ขาดข้ามสาย | CTO vs QA เรื่อง release / งบเกิน Allocation |
| **L5** | Vision / org / core product / R&D scope / audit integrity / budget principle | **STOP + escalate Owner via CEO (+ Legal ถ้า compliance)** — CTO ไม่แตะ | แก้ audit / ดึง R&D / เปลี่ยน scope Phase 1 |

### Veto path (ลัด — ไม่รอ layer)

```
QA FAIL / Security BLOCKED / CFO REJECT / Legal veto
  → CTO STOP ทันที (ห้าม negotiation เอง)
  → escalate CEO พร้อม evidence + trade-off
  → CEO vs ... deadlock ≥3 รอบ → Owner (Dr.solodev) ตัดสิน (ตาม google-ai-insights §Deadlock)
```

- CFO veto งบ: ส่ง Negotiation Loop ผ่าน CEO → CFO (counter-offer / ลดสเกล / เลื่อน) — CTO ไม่ต่อรองเอง
- CEO เคารพ CFO veto (Legacy First / runway <12 เดือน = REJECT)

---

## 5. Audit Path (ไม่ผ่าน CTO)

```
Specialist → Central Bus (auto log)
  → Pipeline Auditor (ตรวจ + เก็บ evidence + compliance check)
  → CEO + Legal (ตุลย์) ตรง — CTO ไม่กรอง ไม่ delay ไม่แก้
```

- CTO มีหน้าที่เดียว: **เปิดทาง + ส่ง Bus pointer ครบ + ไม่แตะ audit**
- Confirmation records (`bus/dispatch/confirmations/`) คือส่วนหนึ่งของ audit — ลบ/แก้ = L5 dealbreaker
- Legal audit ทุก 90 วัน (Governance Policy §5.4) ครอบ CTO ด้วย

---

## 6. PDPA + Log Redaction Gate

- ทุก log/report/handoff ก่อนส่งต่อ: `python3 legal_vault/privacy_guard.py <file-or-dir> [--redact]` (read + scan — ไม่ใช่ write สัญญา)
- เจอ `email / phone / api_key / ssn / ip` → redact เป็น `[REDACTED]` ก่อน commit/ส่ง Bus
- ห้ามมี secret/PII ใน log (Engineering rule #8) — เจอ = STOP + redact + ส่งใหม่
- `legal_vault/**` เป็น read-only สำหรับ CTO — เปลี่ยนแปลงใดๆ ผ่าน Legal + CEO approve เท่านั้น

---

## 7. CFO Budget Gate (ก่อนเริ่มทุกงาน Phase 1)

```
CEO idea → Financial Proposal → CFO (ตรวจ compute/tokens/cash + runway 12 เดือน)
  → APPROVED + Allocation Code → Bus → CTO แตกงานได้
  → REJECTED + counter-offer → CEO ปรับแผน → ส่งกลับ CFO (Negotiation Loop)
```

- CTO ห้ามแตกงาน/สั่ง Eng/QA ก่อนเห็น Allocation Code
- งบเกินกลางทาง → เบรกงาน → ทำ Technical Spec + Infra Cost → ส่ง Negotiation Loop (ตาม CTO profile เดิม §Budget)

---

## 8. CTO vs Orchestrator — ไม่ซ้ำกัน (กันดราม่า)

| เรื่อง | Orchestrator (พี่วุฒิ) นำ | CTO นำ | วิธี sync |
|:-------|:--------------------------|:-------|:----------|
| Pipeline sequencing / queue / monitor / AAR | ✅ เจ้าของ | ให้ status ทางเทคนิค | CTO ส่ง gate verdict เข้า pipeline ที่ Orchestrator คุม |
| Technical gate (Security/Compliance/Quality) | รับ verdict | ✅ เจ้าของ gate | Orchestrator ไม่ปลด gate เอง |
| ตั้ง pipeline ใหม่ cross-dept | ✅ เจ้าของ workflow design | ให้ input ทางเทคนิค | CTO ขอผ่าน Orchestrator ไม่ตั้งทับ |
| Incident P0/P1 cross-dept | ประสาน flow | สั่งหยุดทางเทคนิคถ้า veto | COO ร่วม triage L1–L3 |

---

## 9. C-Level Placement (ยืนยัน — กันตีความผิด)

```
Owner (Dr.solodev) — L5
└── CEO (เทอโบ) — L4
    ├── CTO (เวคเตอร์) — C-Level เทียบ CFO/CMO/COO, reports to CEO ตรง
    ├── CFO (meetoo) — peer, มี veto งบเหนือ CTO
    ├── CMO (มาร์ค) — peer, ต่างสาย (growth) ไม่ขึ้นกัน
    ├── COO (กิจ) — peer, CTO ประสาน daily ops L1–L3 ด้วย
    └── Orchestrator (พี่วุฒิ) — system pipeline (ไม่ใช่ C-Level แต่คุม flow cross-dept)
        ├── Architect / Engineering / QA (coordinated by CTO ใน Phase 1 — แต่ไม่ใช่ลูกน้อง CTO)
        ├── Product (โปรดัค) — peer CTO, reports to CEO ตรง, นอก scope CTO
        └── R&D Lab — Owner-direct, นอก scope CTO เด็ดขาด
```

- **Architect/Engineering/QA ไม่ใช่ลูกน้อง CTO** — ทุก Head reports to CEO ตรง; CTO สั่งผ่าน handoff ไม่ใช่สายบังคับบัญชา
- **Product/R&D อยู่นอก CTO** — peer + Owner-direct; เอกสารใดบอกว่าเป็นใต้ CTO = ผิด red line

---

*DRAFT โดย Legal (ตุลย์) — ยังไม่มีผลบังคับใช้จนกว่า CEO + Owner เซ็น L5 — ห้ามอ้างเป็น policy จริง*

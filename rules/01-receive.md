# 01 — รับ request: assess → filter → route → handoff

> **เมื่อ Owner หรือระบบส่ง request มา — นี่คือวิธีจัดการทั้งหมดในที่เดียว**

## 1. Assess — ดูว่าอะไรสำคัญ

| Priority | อะไร | ตัวอย่าง |
|:---------|:-----|:---------|
| **P0** | ระบบล่ม, data loss, security incident | Bus ล้ม, มี breach |
| **P1** | Feature หลักเสีย, deadline ใกล้ | Deploy ล้มเหลว, CI/CD ตาย |
| **P2** | งานประจำ, feature ใหม่ | เพิ่ม endpoint, แก้บั๊ก |
| **P3** | อนาคต, วิจัย, improve | Refactor, experiment |

## 2. Filter — Mirror Check + Escalate

### Auto-Mirror (L3+ auto run โดย system)
```bash
/mirror department=<dept> decision=<decision> priority=<P0-P3>
# → auto LLM evaluation, audit trail, PASS/FAIL/ESCALATE
```
System รัน mirror check auto สำหรับ L3+ — ผมไม่ต้อง consciously นึก

### Mirror Check (3 คำถาม — manual backup)
1. Owner อนุมัติแนวทางนี้ล่วงหน้าไหม? (pre-approved scope?)
2. ทางเลือกอื่นดีกว่าหรือเปล่า? (effort, impact, risk)
3. ถ้า Owner มาเห็นทีหลัง จะ approve ไหม?

### Escalation Filter (L1-L5)

| ระดับ | อะไร | action |
|:-----:|:-----|:-------|
| **L5** | Vision, Org structure, Core product rewrite | ✅ **ถึง Owner** |
| **L4** | Cross-dept strategy, budget ใหญ่, roadmap shift | CEO ตัดสิน → รายงาน |
| **L3** | Cross-dept handoff, feature decision | Department Heads |
| **L2** | Daily ops, fix, bug, deploy | Specialist Agents |
| **L1** | Routine, auto | Loop Runner / Auto-pilot |

**หลัก:** Owner ตัดสินใจ 20-30% — เรา operate 70-80% ไม่ต้องถาม permission

## 3. Route — request นี้ไปแผนกไหน?

| คำสำคัญ | แผนก | เรียก |
|:--------|:-----|:------|
| vision, strategy, decision | CEO (เทอโบ) | `@ceo-turbo` |
| การเงิน, งบ, cost, budget | CFO (meetoo) | `@cfo-meetoo` |
| การตลาด, brand, content, social | CMO (มาร์ค) | `@cmo-mark` |
| pipeline, orchestration, workflow | Orchestrator (พี่วุฒิ) | `@orchestrator-wut` |
| architecture, bus, routing, system | Architect (พี่ทรงศักดิ์) | `@architect-songsak` |
| product, feature, PRD, roadmap | Product (โปรดัค) | `@product-produck` |
| code, backend, frontend, implement | Engineering (ช่างฟูล) | `@changful` |
| UX, design system, brand visual | Design (ครีเอท) | `@design-kreet` |
| UI, component, interface | UI Designer | `@ui-designer` |
| test, QA, bug, quality | QA | `@qa` |
| sales, deal, pipeline | Sales (เซลส์) | `@sales` |
| support, customer | Support (ซัพพอร์ต) | `@support` |
| legal, compliance, contract | Legal (ตุลย์) | `@legal-tulya` |
| blockchain, solana, DeFi, smart contract | Web3 (อัยวา) | `@web3-aywa` |
| content, caption, video, campaign | Content (เสก) | `@content-creator-sek` |
| network, CDN, VPN, DNS, infra | NetEng (นีต) | `@neteng-neet` |
| security, threat, incident, IR | CyberSec (ซาย) | `@cybersec-sai` |
| psychology, behavior, bias, UX research | Psychology (จิต) | `@psych-jit` |
| research, prototype, experiment | R&D Lab | `@rd-lab` |

**กฏ:**
- request ไม่อยู่ใน scope ไหน → route ไป CEO (เทอโบ)
- request ข้ามหลายแผนก → ระบุ department ที่ต้องประสาน
- ทำงานใน **บทบาทหัวหน้า** ไม่ใช่ specialist

## 4. Handoff — ส่งต่องานอย่างมี structure

### Slash Commands

| คำสั่ง | เมื่อไหร่ |
|:------|:---------|
| `/handoff <from> <to> <task>` | ส่งต่องานแบบมี context pack |
| `/pipeline-bridge <from> <to> <task>` | ส่งข้ามแผนก มี audit trail |
| `/pipeline <feature>` | รัน pipeline เต็ม Spec→Plan→Build→QA→Deliver |
| `/route <request>` | ให้ระบบ classify ว่าไปแผนกไหน |

### Structured handoff JSON

```json
{
  "handoff": {
    "from": "Head A", "to": "Head B",
    "work_item": "task-id", "status": "ready",
    "artifacts": ["path/to/artifacts"],
    "deadline": "YYYY-MM-DD", "priority": "high"
  }
}
```

**ทุก handoff ต้องมี:**
- current state summary
- artifacts (files, decisions, pending)
- context pack — ตัดสินใจอะไรไปแล้วบ้าง
- receiver confirmation

## 5. Pillars — ข้อห้ามตอนทำงาน

- ❌ **Head ลงมือ implement เอง** — delegate ให้ specialist เสมอ
- ❌ **Orphan work** — ทุกงานต้องมีเจ้าของ
- ❌ **Specialist คุยข้าม department ตรงๆ** — ผ่าน Central Bus เท่านั้น
- ✅ Head = outcome owner, ไม่ใช่ task doer

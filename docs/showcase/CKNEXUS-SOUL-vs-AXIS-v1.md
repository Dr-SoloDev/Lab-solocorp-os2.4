# CK-NEXUS PR #384 (SOUL + Skill Foundry) vs SoloCorp OS / AXIS — โชว์เทพ Wave 1 รีวิว
# CK-NEXUS PR #384 vs SoloCorp OS / AXIS — Wave 1 Showcase Review

> สถานะ (Status): D1 — โน้ต 1 หน้า เหตุผล+ขอบเขต+เส้นชัย (D1 — one-page rationale, scope, acceptance)
> ขอบเขต (Scope): รีวิวเปรียบเทียบอย่างเดียว ห้าม implement ห้าม merge — Fork/PR only
> แหล่งเขา (Their source): `spinlnw10-art/ck-nexus` PR #384 `feat: integrate SOUL identity and Skill Foundry pipeline` โดย `toyotati1203-beep` (Draft, 22 commits, base `main` ← `research/ai-company-os-intel-20261119`)
> ฝั่งเรา (Our side): SoloCorp OS / AXIS — 19 Departments + 81+ agents, Two-Tier (Control vs Data ผ่าน Central Bus), Heads Lead Agents Execute, SOUL.md ทุกแผนกใน `profiles/`
> Branch: เป้าหมาย `feat/showcase-cknexus-20261119` ไม่มีในเครื่อง — ทำงานบน HEAD ปัจจุบัน (detached) แล้วแจ้งตามคำสั่ง

## 1. สรุป 7 Roles เขา vs 19 Depts เรา — Comparison Table

| # | CK-NEXUS 7 Roles (PR #384 `creator_app/ai_team/souls/*.md`) | บทบาทเขา (Their role) | เทียบ SoloCorp OS / AXIS (Our counterpart) | หมายเหตุสถาปัตย์ (Architect note) |
|:-:|:-------------------------------------------------------------|:-----------------------|:--------------------------------------------|:-----------------------------------|
| 1 | `director.md` — Lead Orchestrator | สั่งทีม + รวม debate (TeamDirector + debate synthesizer) | `04-orchestrator` พี่วุฒิ + `01-ceo` เทอโบ | เขา = 1 role ควบ orchestrate+synthesize; เราแยก CEO (strategy/final call) ออกจาก Orchestrator (pipeline coordination) ชัดเจนกว่า |
| 2 | `engineer.md` — Specialist | ลงมือ build (DevTeamRuntime OpenAI Agents SDK, 1 ใน 5 specialists) | `07-engineering` ช่างฟูล (+ `cto` primary) | เขา inject SOUL ลง live prompt; เราแยก Control (Head) vs Data (specialist ผ่าน Bus) — Head ห้าม implement เอง |
| 3 | `designer.md` — Specialist | ออกแบบ (1 ใน 5 specialists) | `08-design` ครีเอท + `09-ui-designer` | เราแยก Design (UX research/brand) vs UI-Designer (component/interface) เป็น 2 แผนก; เขารวมใน role เดียว |
| 4 | `analyst.md` — Specialist | วิเคราะห์ (1 ใน 5 specialists) | `10-qa` (Test Results Analyzer) + `12-support` (Analytics Reporter) + `02-cfo` (Riley/Morgan) | เรากระจาย analyst ตามโดเมน (QA/finance/support); เขารวมเป็น role เดียวกลางทีม dev |
| 5 | `researcher.md` — Specialist | ค้นคว้า (1 ใน 5 specialists + Research/Knowledge repo tenant-scoped) | `19-rd-lab` (Lead Researcher + 7 specialists) + `18-psychology` (behavior) | เรามีทั้งแล็บอิสระ (ไม่ผ่าน pipeline) + Knowledge Curator; เขาเป็น repo tenant-scoped ผูกทีม dev |
| 6 | `connector.md` — Specialist | เชื่อมต่อ/integration (1 ใน 5 specialists) | `05-architect` พี่ทรงศักดิ์ (Central Bus, routing, `routing.yaml`) + `16-neteng` นีต | เราเป็น Bus + routing.yaml + circuit breaker ระดับ org; เขาเป็น role เชื่อมในทีม |
| 7 | `guardian.md` — QA/Safety | คุมคุณภาพ/ความปลอดภัย + evidence lineage (QUARANTINED, activation ไม่อนุญาต) | `10-qa` QA-ทีม + `17-cybersec` ซาย + `13-legal` ตุลย์ + `pipeline-auditor` | เรามี QA + CyberSec + Legal + audit trail แยกกัน 4 ชั้น; เขา QUARANTINED drafts + append-only lineage แต่ยังไม่มี activation path |
| + | `common.md` (shared) | guidance กลางทุก role | `profiles/TEMPLATE-5LAYER.md` + `rules/INDEX.md` + SOUL.md ทุกแผนก | เรา version SOUL ระดับ org (template + rules + per-dept SOUL); เขา version SOUL ระดับ repo ผ่าน `soul.py` + TeamDirector context |

แผนกเรา 19 ที่ไม่มีคู่ตรงใน 7 roles เขา (Our 19 with no direct counterpart — proves scope difference): CFO (meetoo), CMO (มาร์ค), COO (กิจ), Product (โปรดัค), Sales (เซลส์), Support (ซัพพอร์ต), Legal (ตุลย์), Web3 (อัยวา), Content Creator (เสก), NetEng (นีต), CyberSec (ซาย), Psychology (จิต) — สรุป: เขาคือ **DevTeam-scoped AI team (7 roles)** ส่วนเราคือ **Company OS (19 depts, 81+ agents)** คนละชั้นกันโดยออกแบบ (They are a dev-team; we are a company OS — different layers by design).

## 2. จุดเสริมกัน 3 ข้อ — Complementary Points (3)

1. **SOUL แบบ versioned + inject ลง live prompt (Versioned SOUL injected into live prompts)** — เขา `soul.py` พา SOUL metadata ผ่าน TeamDirector context ลง DevTeamRuntime instructions จริง (5 specialists + Lead + synthesizer) พร้อม regression tests (`test_agent_soul.py`, 78 passed) — เราเอาแพทเทิร์น `SOUL → task context → live instructions + test` นี้ไปเสริม `profiles/` + SkillHub ได้โดยไม่รื้อ Two-Tier
2. **Skill Foundry contracts + QUARANTINED activation (Quarantined skill pipeline)** — เขาแยก contracts (`skill_foundry.py`) ออกจาก pipeline (`skill_foundry_pipeline.py`) + Idea Engine + tenant-scoped Research/Knowledge repos + append-only evidence lineage โดย draft ค้าง QUARANTINED ห้าม activate — ตรงกับ Certification Ladder เรา (D1→D4, default NOT PASSED, maker≠checker) เอามาเป็น reference implementation ของ publish gate ได้
3. **Fail-closed evidence gates บน CI (Fail-closed CI evidence gates)** — เขา `candidate-automated-gates.yml` + `q10-evidence-gate.yml` ตรวจ attack report validity (tests_total/passed/failed สอดคล้องกัน) ไม่ผ่าน = NOT_VERIFIED ห้าม promote + pinned TLS probe + digest-pinned base image — เราเอาเกณฑ์ fail-closed นี้ไปเสริม `workers/auto_qa_gate.py` (threshold 9) + bus evidence (`bus/evidence/`) ได้ทันที

## 3. จุดซ้ำซ้อน 2 ข้อ — Overlaps (2)

1. **SOUL identity ซ้ำชั้น (Overlapping SOUL layers)** — ทั้งคู่มี SOUL-as-behavioral-guidance (grants no permissions) + versioned + per-role/dept — ถ้า import ของเขาตรง ๆ จะมี 2 source of truth (`creator_app/ai_team/souls/` vs `profiles/*/SOUL.md`) ต้องเลือกข้างเดียว: `profiles/` เป็น canonical แล้ว map ของเขาเป็น adapter เท่านั้น
2. **Skill/Idea pipeline ซ้ำกับ R&D + Content pipeline (Overlapping idea-to-skill pipelines)** — Idea Engine + Skill Foundry ของเขาชนกับ `19-rd-lab` (Prototyper/Experiment Designer/Tool Smith/Knowledge Curator) + Content Creator governed chain (`ingest→script→visual→cue→render→gate→approval`) ของเรา — ห้ามรัน 2 pipeline คู่ขนาน ต้องให้งาน skill ใหม่วิ่งเส้นเดียวผ่าน Central Bus

## 4. ความเสี่ยง 2 ข้อ — Risks (2)

1. **Draft + QUARANTINED + full-suite ไม่ผ่าน (Draft risk — quarantined, no full-suite pass)** — PR ยังเป็น Draft, CodeRabbit ยังไม่รีวิว draft อัตโนมัติ, ผู้ทำประกาศเองว่า full pytest เก็บไม่ได้ (ขาด FastAPI/SQLAlchemy/MCP/defusedxml/dotenv บน Termux) และไม่ claim full-suite pass — ห้าม merge ห้ามอ้างเป็น production proof; consume ได้แค่แบบอ่าน + Fork อ้างอิง
2. **Tenant-scoped repo + API key ผ่าน TLS probe (Tenant isolation + secret handling risk)** — Research/Knowledge repos แยกตาม tenant + `collect_dev_status.py` ส่ง API key ผ่าน TLS (Advanced Security bot ติงแล้ว) — ถ้าเอามาต้องผ่าน Legal + CyberSec review ก่อน (tenant boundary, secret scan, provenance `client_supplied_unverified` แบบ Content Pack เรา) มิฉะนั้นเสี่ยง key leak ข้าม tenant

## 5. ข้อเสนอ POC 1 ข้อ — POC Proposal (Fork/PR only, 1 item)

**POC: SOUL-context adapter อ่านอย่างเดียวจาก Fork (Read-only SOUL-context adapter from a Fork)** — Fork `ck-nexus` ที่ PR #384 commit มาอ่าน `souls/*.md` + `skill_foundry*.py` contracts อย่างเดียว แล้วเขียน adapter ฝั่งเราฝั่งเดียวใน `docs/showcase/` + `skills/@axis/` (ห้ามแตะ `profiles/*/SOUL.md` ตัวจริง ห้ามแตะ bus/prod): map 7 roles เขา → 19 depts เราตามตาราง §1, replay `test_agent_soul.py` 78 tests แบบอ่านอย่างเดียว, เดิน Skill Foundry 1 skill ตัวอย่างจบที่ QUARANTINED + evidence ลง `bus/evidence/` (gate fail-closed แบบเขา) แล้วขอ QA ตรวจแบบ maker≠checker (Maker: Architect, Checker: QA) — สำเร็จ = D2 mini-agent รันได้ + ตาราง D3 ≥20 งาน; ล้มเหลว = รายงาน blocked พร้อมหลักฐาน (ถือเป็นผลงานที่ถูกต้อง) — ไม่มี merge ข้าม repo เด็ดขาด

---
*เส้นชัย D1 (D1 acceptance): ไฟล์นี้มีครบ ตาราง 7-vs-19 + เสริม 3 + ซ้ำ 2 + เสี่ยง 2 + POC 1 (Fork/PR only) + footer SHA-256/วันที่/ผู้ทำ-ผู้ตรวจ + ไม่แตะไฟล์นอก `docs/showcase/`*

---
## ภาคผนวกความสมบูรณ์ — Integrity Footer (ต่อท้ายตามคำสั่ง)

- SHA-256 ของ body v1 (ก่อน footer นี้, computed 2026-11-19T10:31:36Z): `0b50b2237c4168c17c42c505da0ab4123b8e54d091b9d63b87c3ce5854e5becb`
- วันที่ (Date, UTC): 2026-11-19T10:31:36Z (Thu Nov 19 2026) — ปรับเป็นเวลาจริงตอนตรวจซ้ำด้วย `date -u +%Y-%m-%dT%H:%M:%SZ`
- ผู้ทำ (Maker): Architect — พี่ทรงศักดิ์ (System Architect & Central Bus)
- ผู้ตรวจ (Checker): QA — QA-ทีม (maker≠checker, default NOT PASSED จนกว่า QA attach หลักฐาน)
- Branch: `feat/showcase-cknexus-20261119` ไม่มีในเครื่อง — สร้างไฟล์บน HEAD ปัจจุบัน (detached HEAD) ตามคำสั่ง fallback แล้วแจ้ง
- วิธีตรวจซ้ำ (Reproduce): `sha256sum docs/showcase/CKNEXUS-SOUL-vs-AXIS-v1.md` แล้วเทียบ body — footer นี้จงใจอยู่นอก hash (hash ข้างบนคือของ body ก่อน footer เพื่อเลี่ยง circular hash); รันต่อได้โดยคนอื่น (D1 hobandoff-ready)

# 📦 CKNEXUS-PR-DRAFT-v1 — ร่าง Comment พร้อมส่งกลับ Issue #385 (spinlnw10-art/ck-nexus)
# 📦 CKNEXUS-PR-DRAFT-v1 — Ready-to-Post Comment Draft for Issue #385

> สถานะ (Status): D1 draft — ร่างพร้อม copy ไป post ห้าม post โดย agent (Agent must NOT post — CEO posts manually)
> ปลายทาง (Target): Comment ใน `spinlnw10-art/ck-nexus` Issue #385 (อ้างอิง PR #384)
> เหตุที่ส่งเป็น Comment ไม่ใช่ cross-repo PR ตรง (Why comment, not direct PR): คนละ codebase กัน — เปิด PR ข้าม repo ตรง ๆ ทำไม่ได้ จึงส่งเป็น Offering + วิธีนำไปใช้ต่อ (Different codebases — direct cross-repo PR is not possible; offering + reuse path instead)
> วันที่ร่าง (Drafted, UTC): 2026-11-19
> ผู้ร่าง (Maker): Architect — พี่ทรงศักดิ์ (System Architect & Central Bus)
> ผู้ตรวจ (Checker): QA — QA-ทีม (maker≠checker, รอ attach หลักฐานตรวจร่างนี้ก่อน post)

---

## ✂️ ส่วนที่ copy ไป post ได้เลย (COPY BELOW THIS LINE) — Ready-to-Post Body

### Title (หัวข้อ comment)

`[Showcase Offering] AXIS → CK-NEXUS: ส่งของจริงแล้ว — SOUL 7-vs-19 Review + D2 Adapter (Fork/PR only, Ref #385 / PR #384)`

### Body (เนื้อหา comment)

สวัสดีทีม CK-NEXUS ครับ — ฝั่ง AXIS (SoloCorp OS) ส่งของจริงมาแล้วครับ 🙏
Hello CK-NEXUS team — AXIS (SoloCorp OS) has a working showcase to offer.

> งานนี้ทำบน repo ฝั่งเรา เสร็จบน branch `feat/showcase-cknexus-20261119` commit `6e572f872a7bcdc8c2d00d834fe85b797681ccb4` (5 files, 276 insertions, ไม่แตะโค้ดอื่น) — เนื่องจากคนละ codebase กัน ผมจึงไม่ได้เปิด cross-repo PR ตรง แต่ขอมอบของ + วิธีเอาไปใช้ต่อตามด้านล่างครับ
> Done on our side on branch `feat/showcase-cknexus-20261119`, commit `6e572f872a7bcdc8c2d00d834fe85b797681ccb4` (5 files, 276 insertions, no other code touched) — as we are on different codebases I am not opening a direct cross-repo PR; instead here is the offering + reuse path below.

**1. Summary (สรุปสิ่งที่ส่งมอบ)**

- รีวิวเปรียบเทียบ `CK-NEXUS PR #384 (SOUL + Skill Foundry, 7 roles)` vs `SoloCorp OS / AXIS (19 departments, 81+ agents, Two-Tier Control vs Data)` — สรุปว่าเขาคือ **DevTeam-scoped AI team (7 roles)** ส่วนเราคือ **Company OS (19 depts)** คนละชั้นกันโดยออกแบบ พร้อมจุดเสริมกัน 3 ข้อ / จุดซ้ำซ้อน 2 ข้อ / ความเสี่ยง 2 ข้อ / ข้อเสนอ POC 1 ข้อ (Fork/PR only)
- Comparison review of `CK-NEXUS PR #384 (SOUL + Skill Foundry, 7 roles)` vs `SoloCorp OS / AXIS (19 departments, 81+ agents, Two-Tier)` — you are a dev-team layer, we are a company-OS layer, by design; plus 3 complementary points / 2 overlaps / 2 risks / 1 POC proposal (Fork/PR only).
- D2 adapter ใช้งานได้จริง: แปลง 7 roles เขา → รูปแบบ dept ฝั่งเรา (pure stdlib, ไม่มี LLM/เน็ตเวิร์ก/secrets) + ชุดเทสต์ 6 ข้อผ่าน + ขอบเขต legal ที่ตรวจแล้ว
- Working D2 adapter: maps their 7 roles → our dept format (pure stdlib, no LLM/network/secrets) + 6 passing tests + reviewed legal scope.

**2. Files (ไฟล์ที่ส่งมอบ — อยู่ใน repo ฝั่ง AXIS, commit ข้างบน)**

| # | ไฟล์ (File) | ขนาด (Size) | คืออะไร (What) |
|:-:|:------------|:------------|:---------------|
| 1 | `docs/showcase/CKNEXUS-SOUL-vs-AXIS-v1.md` | 56 บรรทัด (SHA body `0b50b22…4e5becb`) | โน้ตรีวิว D1: ตาราง 7-vs-19 + เสริม 3 + ซ้ำ 2 + เสี่ยง 2 + POC 1 |
| 2 | `docs/showcase/LEGAL-SCOPE-v1.md` | 44 บรรทัด | ใบรับรองขอบเขต: อนุญาต 6 ข้อ / ห้าม 5 ข้อ / license checklist 4 ข้อ (Legal ตุลย์ตรวจแล้ว ✅) |
| 3 | `workers/showcase/cknexus_soul_adapter.py` | 109 บรรทัด | D2 adapter ตัวจริง: `adapt()` + `validate()` (forbidden-token guard + evidence fields), pure stdlib |
| 4 | `workers/showcase/test_cknexus_soul_adapter.py` | 67 บรรทัด | เทสต์ 6 ข้อ (ดู §3) |
| 5 | `workers/showcase/__init__.py` | 0 บรรทัด (marker) | package marker ว่างเปล่า |

**3. Verification (หลักฐานการตรวจ — Reproducible)**

- ผลเทสต์: **6 passed, EXIT 0** — `test_adapt_maps_all_seven_roles` / `test_adapt_rejects_wrong_count` / `test_validate_accepts_clean_mapping` / `test_validate_catches_excess_permission` / `test_validate_catches_missing_evidence` / `test_demo_main_does_not_crash`
- Test result: **6 passed, EXIT 0** (same 6 tests).
- รันซ้ำได้ด้วย: `python -m pytest workers/showcase/test_cknexus_soul_adapter.py -q`
- Reproduce with: `python -m pytest workers/showcase/test_cknexus_soul_adapter.py -q`
- QA: **PASS, maker≠checker** (Maker: Architect พี่ทรงศักดิ์ / Checker: QA-ทีม) — รายงาน "เสร็จ" มีหลักฐานผูก ไม่ใช่คำกล่าวอ้างลอย ๆ
- QA: **PASS, maker≠checker** (Maker: Architect / Checker: QA team) — done-claim is evidence-bound.

**4. Security boundary (ขอบเขตความปลอดภัย — ยืนยันชัด)**

- `Fork / PR only` — ไม่ push ตรงไป upstream ไม่ขอสิทธิ์ write/admin/deploy ใด ๆ ทั้งสิ้น
- `Fork / PR only` — no direct push to upstream; no write/admin/deploy requested whatsoever.
- `No secrets` — ไม่แตะ secrets/tokens/credentials/`.env` ทุกกรณี; adapter ไม่มีคีย์ ไม่มีเน็ตเวิร์ก
- `No secrets` — no secrets/tokens/credentials/`.env` touched in any case; adapter has no keys, no network.
- `QUARANTINED` — งาน skill ใหม่จบที่ QUARANTINED + evidence ลง `bus/evidence/` ตาม fail-closed gate แบบ PR #384 (ห้าม activate จนกว่าจะผ่าน review-test-security gate)
- `QUARANTINED` — new-skill work ends at QUARANTINED + evidence in `bus/evidence/` per PR #384-style fail-closed gate (no activation before review-test-security gates pass).
- License: โค้ดที่นำมาใช้ร่วมกันต้องผ่าน license check ก่อนทุกครั้ง (SPDX + attribution ครบ) — ฉบับนี้ adapter เขียนใหม่ฝั่งเรา 100% จึงไม่มีประเด็นคัดลอก
- License: any shared code must pass a license check first (SPDX + full attribution) — this adapter is 100% newly written on our side, so no copy concern.

**5. How to reuse (วิธีเอาไปใช้ต่อ — เลือกได้ 2 ทาง)**

- **ทาง A (แนะนำ / Recommended — copy ไฟล์เดียว):** copy ไฟล์เดียว `workers/showcase/cknexus_soul_adapter.py` (pure stdlib, zero dependency) ไปวางใน repo ท่าน แล้ว `import` เรียก `adapt(roles7)` + `validate(mapping)` ได้ทันที — ตัวอย่าง 7 roles อยู่ใน `CANONICAL_7` ท้ายไฟล์ (รัน `python -m workers.showcase.cknexus_soul_adapter` ดู JSON ตัวอย่างได้)
- **Option A (recommended — copy one file):** copy the single file `workers/showcase/cknexus_soul_adapter.py` (pure stdlib, zero dependency) into your repo, then call `adapt(roles7)` + `validate(mapping)` — 7-role example lives in `CANONICAL_7` (run `python -m workers.showcase.cknexus_soul_adapter` for sample JSON).
- **ทาง B (ทั้งก้อน / Whole set — cherry-pick):** `git fetch <axis-remote> feat/showcase-cknexus-20261119 && git cherry-pick 6e572f872a7bcdc8c2d00d834fe85b797681ccb4` จะได้ 5 ไฟล์ 276 บรรทัดครบชุด (review doc + legal scope + adapter + tests) โดยไม่ดึงประวัติอื่นติดมา
- **Option B (whole set — cherry-pick):** `git fetch <axis-remote> feat/showcase-cknexus-20261119 && git cherry-pick 6e572f872a7bcdc8c2d00d834fe85b797681ccb4` gets all 5 files / 276 lines (review doc + legal scope + adapter + tests) with no extra history.
- ไม่ต้อง merge ข้าม repo — ท่านเป็นเจ้าของการตัดสินใจฝั่งท่านเต็มที่ครับ (No cross-repo merge needed — the call on your side is 100% yours.)

**6. Ref (อ้างอิง)**

- Ref: Issue #385 (thread นี้) + PR #384 (`feat: integrate SOUL identity and Skill Foundry pipeline` โดย `toyotati1203-beep`, base `main` ← `research/ai-company-os-intel-20261119`)
- ถ้าท่านเห็นว่ามีประโยชน์ ผมยินดีเปิด PR ฝั่งท่านแบบ Fork → PR ตามกติกาท่านทุกประการ (review + test + security gate ครบก่อน merge) — แจ้งมาได้เลยครับ
- If useful, I am happy to open a Fork → PR on your side under your rules (review + test + security gates before merge) — just say the word.

ขอบคุณที่เปิดพื้นที่ให้ cosmology สองฝั่งได้คุยกันครับ 🙏
Thanks for the space where both cosmologies can meet.

— พี่ทรงศักดิ์ (AXIS Architect, SoloCorp OS) | `profiles/05-architect/SOUL.md`

### ✂️ จบบล็อก copy (END COPY BLOCK)

---

## ภาคผนวกสำหรับ CEO (ไม่ต้อง post — CEO-only notes)

1. ไฟล์นี้อยู่บน branch เดิม `feat/showcase-cknexus-20261119` ยังไม่ commit — CEO ตรวจ diff แล้วค่อย `git add docs/showcase/CKNEXUS-PR-DRAFT-v1.md && git commit` ตามนโยบาย (ห้าม commit ถ้ายังไม่เห็น `git status` + `git diff`)
2. Agent (Architect) ห้าม post เองเด็ดขาด — ร่างนี้ให้ CEO เป็นผู้ post ด้วยบัญชีมนุษย์เท่านั้น (ห้ามผูก secrets/token ใน comment)
3. ก่อน post ตรวจ 3 อย่าง: (ก) commit hash `6e572f8` ยังตรง HEAD (ข) SHA body `0b50b22…` ยังตรงไฟล์รีวิว (ค) QA PASS maker≠checker ยังมีผล
4. ถ้าฝั่ง CK ตอบรับทาง A/B ให้เปิดงานใหม่แบบ Fork → PR เท่านั้น (ห้าม push ตรง) + ผ่าน Legal (ตุลย์) + CyberSec (ซาย) review ก่อนทุกครั้ง

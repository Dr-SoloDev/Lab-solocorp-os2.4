# Legacy Inventory — Phase 4 (2026-11-07)

> **สถานะ:** D1 only — decision + inventory only, **D0/NOT PASSED**. ไม่มีการแก้ code/config/rename ใน task นี้
> **Follow-up (2026-11-07, CEO-ordered):** FIX ทั้ง 8 แถว (F1–F8) ถูก apply กับเอกสารเป้าหมายแล้ว — ดูตาราง FIX (คอลัมน์สถานะ); DELETE ยัง 0
> **ขอบเขต grep:** `docs/`, `axis_mcp/`, `scripts/`, `tests/`
> **Benign default:** Phase 4 = flag-only — **ไม่มีการลบ (DELETE) ใด ๆ** จนกว่า Owner จะสั่งแยก task

---

## กฎการจำแนก (ตาม kickoff)

| ประเภท | ความหมาย |
|:--|:--|
| **KEEP** | ปัจจุบัน (current) ไม่ใช่ legacy — ห้าม rename/remove |
| **FIX** | claim ที่ขัดกับ Phase 1–3 reality — ให้ file:line + wording ที่ถูกต้อง (ไม่แก้ใน task นี้) |
| **DELETE** | dead flow/code ที่พิสูจน์แล้วว่าไม่ใช้ — เฉพาะที่มี grep evidence; default คือ flag-only ไม่มีลบ Phase 4 |

---

## ผลการตรวจ (grep — สรุป)

### 1. `render not implemented` / `TODO render` — ไม่พบ legacy drain

| คำค้น | ผล |
|:--|:--|
| `not implemented` ใน `docs/` | เจอ 2: `docs/superpowers/plans/2026-07-05-engineering-qa-fixes.md:630` (ENG-03 Guard engine — historical fix log) · `docs/prds/PRD-Multi-Platform-Compatibility-v1.0.md:58` (legend คำนิยาม) — **ทั้งคู่ไม่ใช่ render claim** |
| `TODO.*render` / `render.*not implemented` | ไม่พบ |
| `not implemented` ใน `axis_mcp/` , `scripts/` , `tests/` | ไม่พบ |

สรุป: ไม่พบ claim ว่า "render ยังไม่ implemented" ที่ขัดกับ Phase 1–3 (render พิสูจน์แล้วทุก phase)

### 2. ffmpeg-skill เป็น renderer — ไม่พบ claim ผิด (ทุกที่ระบุชัดว่าเป็น bridge/plan)

| File:line | คำอ้างปัจจุบัน | เหตุผลที่ KEEP |
|:--|:--|:--|
| `docs/certification/D1-content-ffmpeg-integration.md:10,29-31,39,50` | "Content MCP must not run FFmpeg itself" + manifest/result recorder สำหรับ response ของ ffmpeg-skill | ถูกต้อง — bridge เก็บ plan/result ไม่ execute |
| `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md:35-40,193-194` | `ffmpeg-skill 2.17.1` มีในเครื่องแต่ doctor `ok: false` (7.0.2-static เก่ากว่า CVE-2026-8461, ไม่มี `drawtext`); local renderer ใช้ `provider: ffmpeg-cli`, `execution_mode: local_ffmpeg_cli` และ "must never be sent to `record_ffmpeg_job_result`" | ถูกต้อง + ชัดเจน — ไม่ใช่ renderer |
| `axis_mcp/departments/content_skills/media-production/SKILL.md:36-38` | "The FFmpeg-skill bridge only stores/records a tool plan; it is not the local FFmpeg executable and does not edit a video" | ถูกต้อง |
| `docs/runbooks/CONTENT-CREATOR-STORY-60S.md:28` | "The ffmpeg-skill manifest is a stored check plan only" | ถูกต้อง — ไม่ execute |
| `scripts/render_campaign_media_local.py` | ใช้ FFmpeg CLI ตรง (subprocess ffmpeg/ffprobe) | ถูกต้อง — ไม่ได้เรียก ffmpeg-skill MCP |

สรุป: **ไม่มี claim ที่ ffmpeg-skill เป็น renderer** — จำแนกทั้งหมดเป็น **KEEP**

### 3. Concat-as-default โดยไม่แยก local — จำแนกแยกเป็น FIX/KEEP

- ความแตกต่าง path (Concat continuous vs local per-scene) ถูกต้องและมีอยู่ใน SKILL + runbook แล้ว:
  - `SKILL.md:26-28` และ `CONTENT-LOCAL-MEDIA-RENDER.md:84-86` — "Local rendering is per-scene … Concat is continuous … Never feed local-render artifacts into Concat" — **KEEP**
- แต่คำว่า **"default"** ใน SKILL + runbook พูดเหมือน Concat พร้อมใช้เสมอ บน host นี้ — ไม่จริงหลัง FUSE failure — **FIX** (ดูแถว FIX ในตาราง → **APPLIED 2026-11-07**)

### 4. auto-approval / auto-publish claims — ไม่พบ claim ผิด (gate ถูกต้องทุกที่)

| File:line | คำอ้างปัจจุบัน |
|:--|:--|
| `axis_mcp/departments/content_mcp.py:70-93` | "store artifacts without publishing", "never approves work", "never silently skip … or publish automatically", "Every publication requires recorded human approval" |
| `axis_mcp/departments/content_service.py:2615,2641-2647,2773-2792` | `approval_required: True`, `publish_action: blocked_until_human_approval`, `approved_pending_separate_publish_step` — approval ≠ publish |
| `axis_mcp/departments/media_service.py:378,635-636,663` | "record it without publishing", `"published": False`, `"approval_effect": "none"` |
| `SKILL.md:14,94-95,115` | "no automatic approval or publishing", "This skill never publishes" |
| `docs/plans/MCP-DEPARTMENT-SERVERS-CONTENT-PILOT.md:31` | "review required; no auto-publish" |
| `docs/plans/CONTENT-MANIFEST-ADAPTER-PHASE1.md:140` | "The gate never auto-passes and never auto-approves" |
| `docs/plans/CONTENT-PHASE2-GOVERNED-CALL-GRAPH.md:82` | "Sek calls `record_human_approval` itself … Forbidden … MCP never publishes" |
| `docs/plans/CONTENT-PHASE3-ROBUSTNESS-DESIGN.md:15` | Non-goal: "any auto-approval/publish" — ไม่มี |

สรุป: **ไม่มี claim auto-approval/auto-publish** — ทั้งหมด **KEEP** และควรอ้างอิงเป็นหลักฐานตอน QA

### 5. BYOM / Local-First contradictions — ไม่พบขัดกัน

| File:line | คำอ้างปัจจุบัน |
|:--|:--|
| `docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md:20` | Local-first + hosted multi-user deferred (correct direction) |
| `docs/ARCHITECTURE.md:3` | เอกสารนี้อธิบาย org/agent + Central Bus; product target ให้ยึด PRD local-first — ชี้ถูก (แต่เนื้อหาหลักของ ARCHITECTURE ช้าเกิน — ดู §ARCHITECTURE) |
| `docs/plans/MCP-DEPARTMENT-SERVERS-CONTENT-PILOT.md:18,34` | client-managed LLM + provenance self-reported — สอดคล้อง BYOM |
| `axis_mcp/` grep `BYOM\|bring your own` | ไม่พบขัดกัน |

สรุป: **ไม่พบ contradiction** — **KEEP** (แต่ ARCHITECTURE.md ทั้งไฟล์ช้าเกิน ต้องเติม current-direction — ดู §ARCHITECTURE)

---

## ตารางจำแนก KEEP / FIX / DELETE

### KEEP — ปัจจุบัน ห้ามแตะ (do not rename/remove)

| # | อะไร | File:line (หลักฐาน) | เหตุผล |
|:--|:--|:--|:--|
| K1 | `lifecycle_state = "scaffold"` | `axis_mcp/departments/content_service.py:95` (enum `LIFECYCLE_STATES`), `:488,592,660-781,1049-1930` (~40 refs), `content_helpers.py:210`, `content_mcp.py:409`, `media-production/SKILL.md:33` | **current template-draft lifecycle** — phase สาหรับ draft ที่ยังไม่ validate (ก่อน `client_generated`/`llm_generated`/`human_edited`/`review_required`/`approved`) — kickoff ยืนยันชัดว่า NOT legacy |
| K2 | scaffold asserts ใน tests | `tests/test_content_mcp.py:176,210,473,779-796,856` | ยืนยัน scaffold เป็น draft state ที่ fail 6×15/10×10 validation — behavior ที่ถูกต้อง |
| K3 | ffmpeg-skill bridge คนละตัวกับ FFmpeg CLI | §2 ด้านบนทั้งหมด (`D1-content-ffmpeg-integration`, `CONTENT-LOCAL-MEDIA-RENDER:35-40,193-194`, `SKILL:36-38`) | bridge เก็บ plan/result เท่านั้น — มีบันทึกเรนเดอร์จะไม่เป็น MCP result อยู่แล้ว |
| K4 | Publish Gate ทุกจุด (`review_required`, `blocked_until_human_approval`, `no auto-publish`) | §4 ด้านบนทั้งหมด | เกณฑ์ปัจจุบัน — Phase 1–3 ทุก campaign ยัง `review_required`/`gate_passed: false` |
| K5 | Client-managed provenance (`client_generated`, `client_supplied_unverified`) | `axis_mcp/departments/media_service.py:112,637,739`, `MCP-DEPARTMENT-SERVERS-CONTENT-PILOT.md:18-20` | ปัจจุบัน — BYOM/standalone |
| K6 | `docs/audits/CONTENT-MCP-AUDIT-2026-11-01.md:40,143` (`sound-studio` แยกแผนก) | audit snapshot ก่อน 2026-11-02 | **KEEP เป็น audit** — เป็น snapshot ถูกต้องในวันที่นั้น (2026-11-02 มี `docs/MEDIA-TOOLKIT.md:5-7` บันทึกว่า `sound-studio` ไม่ใช่แผนกแยกอีกต่อไป) — ห้ามแก้ audit ให้เป็นปัจจุบัน (ทำลาย audit trail) |
| K7 | `scripts/render_campaign_media_local.py` + `render_campaign_media_local` | `CONTENT-LOCAL-MEDIA-RENDER.md:5-16`, `SKILL.md:24` | proven path Phase 1–3 — ไม่ใช่ legacy |
| K8 | `docs/runbooks/CONTENT-CREATOR-STORY-60S.md:28` ประโยค Canvas2D render ไม่ใช้ Concat | บรรทัดเดียว path-scoped | KEEP — บอกเฉพาะ render นั้นใช้ Canvas2D+Piper+FFmpeg CLI ไม่ได้ใช้ ffmpeg-skill/Concat (true สำหรับเส้นทางนั้น), ไม่ใช่ claim ระดับ host |

### FIX — claim เก่าขัดกับ Phase 1–3 reality — **ทั้ง 8 แถว APPLY แล้ว (2026-11-07, CEO-ordered)**

> **สถานะแก้ (2026-11-07):** F1–F8 แก้เอกสารเป้าหมายครบแล้วตาม file:line ด้านล่าง (FIX wording ปรับให้ตรงสถานะปัจจุบัน Concat ด้วย: extract + handshake verified 2026-11-07, render ยังไม่ proven — ดู ADR-032 amended). แถวที่ชี้ไปที่เอกสารประวัติ/แผน (F6, F8) ใช้ **append follow-up note** แทน rewrite. **DELETE ยัง 0 — `scripts/content_render.py` ยัง flag-only ห้ามลบ**

| # | Claim ที่เก่า | File:line | wording ที่ถูกต้อง (Phase 1–3 reality) | สถานะ |
|:--|:--|:--|:--|:--|
| F1 | "Concat รันบน Linux ได้จริงแค่ลง binary ให้ถูกต้อง" / "ติดตั้งหลายรูปแบบแล้วเห็นผล D2" — แถมลง binary คือ mount ได้ | `docs/FAMILY.md:44`, `docs/certification/D1-content-creator.md:18` | "Concat 0.2.8 AppImage binary มีจริงบน host นี้ (`Concat-0.2.8-x86_64.AppImage`, ELF) แต่ AppImage ต้องการ FUSE mount ซึ่ง host นี้นอก container ไม่อนุญาต (`fusermount3 Operation not permitted`, exit 127) เลย launch MCP ไม่ได้ — local-media path ไม่ต้องการ Concat และ proven ผ่าน Phase 1–3 แล้ว" (บวก status ปัจจุบัน: extract + handshake verified 2026-11-07, render ยังไม่ proven) | ✅ FIXED (2026-11-07, CEO-ordered) |
| F2 | "Concat installed + registered as MCP" โดยไม่มี suspended โน้ต | `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md:41-47` | เพิ่ม: "บน host นี้ Concat MCP ถูก **suspended (Phase 4 ADR-032)** — FUSE mount denied; local-media render (`render_campaign_media_local`) เป็นเส้นทางหลักของ host นี้; re-enable เป็น `enabled false→true` ใน `opencode.json` เมื่อ host พร้อม" (แทนด้วยสถานะจริง 2026-11-07: FUSE denied = history; extract path สำเร็จ + handshake verified; render ยังไม่ proven; fallback = disable) | ✅ FIXED (2026-11-07, CEO-ordered) |
| F3 | โปรเซสเสียงกล่าว "script → cue → SFX → **Concat render → Earshot → Gate**" เป็น default เส้นเดียว โดยไม่มี local alternative | `docs/MEDIA-TOOLKIT.md:8-12` | "script → cue → SFX/voiceover → **เลือก render path ก่อน** (host นี้: local-media FFmpeg CLI เป็นหลักที่พิสูจน์แล้ว Phase 1–3; Concat ถูก suspended บน host นี้) → Earshot review → Gate → human approval" (ปรับเป็นสถานะจริง: Concat handshake verified แต่ render ยังไม่ proven บน host นี้) | ✅ FIXED (2026-11-07, CEO-ordered) |
| F4 | Concat ติดตั้ง + ลงทะเบียน MCP ทำงาน ( ไม่มี host caveat) | `docs/MEDIA-TOOLKIT.md:39-43` | "ติดตั้ง Concat 0.2.8 AppImage + ลงทะเบียน MCP `concat` — **บน host นี้ FUSE mount denied จึง launch ไม่ได้ (Phase 4 ADR-032)**; evidence render สำเร็จ 2026-10-30 เป็น historical proof ไม่ใช่ current host claim" (ปรับเป็นสถานะจริง: รันจาก `--appimage-extract` path, handshake verified 2026-11-07, render ยังไม่ proven) | ✅ FIXED (2026-11-07, CEO-ordered) |
| F5 | "`render_campaign_with_concat` = Default for launch and story videos" (ไม่มี host qualifier) | `axis_mcp/departments/content_skills/media-production/SKILL.md:23` | "Default for launch/story videos **บน host ที่ Concat ทำงานได้** — **บน host นี้ (FUSE denied) ใช้ `render_campaign_media_local` เส้น local** (ADR-032)" — หมายเหตุ: SKILL.md เป็น Content skill (Sek-owned) — Phase 4 task นี้ flag-only, ห้ามแก้เองใน Architect task | ✅ FIXED (2026-11-07, CEO-ordered — Owner สั่ง apply ทั้ง 8 แถว; wording ปรับเป็น handshake verified + render unproven) |
| F6 | "Rendering remains blocked pending independent patch verification" / "rendering out of scope, label as draft" | `docs/content/2026-10-26-FIRST-CUSTOMER-VALUE-CONTENT-PILOT.md:51,61`, `docs/plans/CONTENT-CUSTOMER-VALUE-PILOT.md:37,80,97` | "> **Superseded (Phase 1–3, 2026-11-07):** synthetic-only render ทำงานได้จริง — locally rendered MP4s ที่ `central_bus/content/local_media/` ผ่าน ffprobe; real user media ยัง blocked จน runtime ได้รับการ independent verification" — pilot doc เป็น historical plan เพิ่มโน้ตแทนการ rewrite | ✅ FIXED (2026-11-07, CEO-ordered — append follow-up note ทั้ง 2 ไฟล์) |
| F7 | "Concat unavailable in this runtime" (ใช้คำว่า unavailable ราวกับไม่มี binary) | `scripts/media/solocorp_power_one_90s.json:8` | "Concat 0.2.8 AppImage binary มีจริง แต่ Concat MCP launch ไม่ได้บน host นี้ (FUSE mount denied); FFmpeg local CLI คือ renderer ที่ใช้" (ปรับเป็นสถานะจริง: รันจาก extract path, handshake verified 2026-11-07, render ยังไม่ proven; FFmpeg local CLI คือ renderer ของ run นี้) | ✅ FIXED (2026-11-07, CEO-ordered) |
| F8 | "Pilot นี้ยังไม่ใช่ app, module registry — OpenCode E2E pending" + tool list 5 เครื่องมือเท่านั้น | `docs/plans/MCP-DEPARTMENT-SERVERS-CONTENT-PILOT.md:3,54-60` | บรรทัด 3 อธิบายฐานะ pilot-vs-app ถูกต้องแล้ว (KEEP เป็น robust) — เพิ่ม pointer ว่า catalog ปัจจุบันมี 16+ tools (ดู `content_mcp.py:334-345`, `test_content_mcp.py:334-345`) และ **ไม่ใช่ "render not implemented"** (render proven Phase 1–3) | ✅ FIXED (2026-11-07, CEO-ordered — append follow-up note) |

### DELETE — ไม่มี (Phase 4 flag-only)

| # | Candidate | grep evidence | สถานะ |
|:--|:--|:--|:--|
| — | `scripts/content_render.py` (202 บรรทัด, D2 Concat renderer) | grep `content_render` ใน `axis_mcp/` = **0 hits**; ใน `tests/` = **0 hits**; เจอเฉพาะ docs `D1-content-creator.md:18,42` (ระบุ D2 **ไม่ใช้** สคริปต์นี้แล้ว) และ `FAMILY.md:44,53` (ฝากงานพิสูจน์) — ไม่มี MCP tool import ไปเรียก | **FLAG เท่านั้น — ยังไม่ DELETE** — พิสูจน์ "ไม่มี code เรียก" แล้วแต่ docs ยังอ้างและ Phase 4 default = flag-only; ต้อง Owner สั่งลบแยก task + เช็กจนถึง `workers/` imports ก่อน |

> ไม่มีไฟล์อื่นที่เข้าเงื่อนไข DELETE (provably unused) — `scripts/render_campaign_media_local.py` + `media_service.py` + `content_service.py` มี MCP tool + tests รองรับครบ

---

## ARCHITECTURE.md staleness assessment (2026-09-27 vs PRD 2026-11-01)

- ไฟล์: `docs/ARCHITECTURE.md`
- สถานะในไฟล์: `Version: 2.4`, `Last Updated: 2026-09-27`, footer `System First, Everything Follows`
- บรรทัด 3 อัปเดตแล้วในปี 2026-11 (ชี้ไป PRD local-first) — **แต่นอกบรรทัดนั้น เนื้อหาหลักหยุดที่ 2026-09-27** คือ 5 สัปดาห์ก่อน PRD MVP v1.0 (2026-11-01)

### ส่วนที่ต้อง targeted current-direction update (ไม่ full rewrite — ตาม kickoff ข้อ 2)

| ส่วน ARCHITECTURE | ปัญหา | แนวทางอัปเดตแบบ targeted |
|:--|:--|:--|
| Header / ขอบเขต (บนสุด) | มีแต่บรรทัด 3 อ้าง PRD แบบ generic | เพิ่มบรรทัดเดียว: "Primary product direction = PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0 (local-first SoloCorp App, MVP = 1 CEO + department MCPs + registry + task queue; Phase 1 = Content Creator pilot E2E) — ตอนนี้ **App shell/registry/provider flow ยังไม่ implemented**; product track แยกจาก org/agent track ข้างล่าง" |
| §Key Design Decisions (ท้ายไฟล์: ADR-001…ADR-005 5 รายการ) | list เก่ามาก — ไม่ถึง ADR-032 | เติมแถว: "Content Creator MCP pilot + open-core boundary (ADR-030) + sound specialist integration (ADR-031) + Concat host suspend (ADR-032)" + ลิงก์ `decisions/` |
| §Department Profiles (19) + §Specialist Sub-Agents (62+) | พูด "19 + 62+ Active" แบบ 2026-09-27 | เติมโน้ต: "จำนวน profiles/agents เปลี่ยนแปลงตาม `.opencode/agents/` + `profiles/INDEX.md` ปัจจุบัน — ดู README §What is actually in the tree (20 profiles · 21 agents)" — ไม่แก้ตัวเลขใน ARCHITECTURE (README เป็น source of truth ของ count) |
| §Loop Runner + §Agent Worker Service | วันที่ loop media_daily 2026-09-28 ไม่สอดคล้องกับ Content Creator governed calls (Phase 2/3) | โน้ต: "Loop Runner เป็น ops cadence; Content Creator call graph + publish gate อยู่ใน Content MCP (phase 1–3) — ดู `docs/plans/CONTENT-PHASE2-GOVERNED-CALL-GRAPH.md` + `CONTENT-PHASE3-ROBUSTNESS-DESIGN.md`" |
| เพิ่ม §Content Creator / Product Packs (ไม่มีเลย) | ARCHITECTURE ไม่กล่าวถึง Content pack ทั้งที่ README อ้างเป็น pack หลัก | เพิ่ม 1 หน้า (ไม่ rewrite ทั้งไฟล์): "Content Creator Pack = 1 governed MCP (16+ tools) + publish gate + media render (local proven Phase 1–3; Concat enabled + handshake verified 2026-11-07 แต่ render ยังไม่ proven บน host นี้ ตาม ADR-032 amended) — ไม่ใช่ finalized product" — **ทำแล้ว 2026-11-07 (§Content Creator Pack ใน ARCHITECTURE)** |

### ส่วนที่ LEAVE ALONE (คงเดิม — ไม่ใช่ legacy)

| ส่วน | เหตุผล |
|:--|:--|
| Principle 1–6, Pillars, Two-Tier, Hierarchy, Communication Protocols, Routing/Circuit Breaker, Exception AXME | เป็น architecture ที่ยังเป็น current org model — PRD ไม่ขัด |
| §LLM Provider (token accounting) | current cross-reference — ไม่เกี่ยวกับ local-first scope |
| ADR-001…ADR-005 table | historical decisions ที่ยัง valid — ไม่ลบออกจากที่มา |
| Footer mission statement | ไม่เกี่ยวกับ architecture staleness |

### ภาษา/รูปแบบ

ARCHITECTURE ใช้อังกฤษเป็นหลัก (README ไทย/อังกฤษผสม) — คงเดิม ใส่ส่วนอัปเดตเป็นอังกฤษล้วน; ไม่เปลี่ยนชื่อไฟล์หรือย้ายตำแหน่ง (ทุกที่อ้าง `docs/ARCHITECTURE.md`)

> ภาษาของการอัปเดต: คงโทนเดียวกับไฟล์เดิม (อังกฤษ) + เพิ่มโน้ต PRD ไทยตามแนว README (README ใช้คำว่า "Current product direction … app is a planned MVP, not a feature already delivered" — อ้างคำนั้นตรง ๆ ไม่แต่งใหม่)

---

## สรุป Phase 4 (ที่ Owner ต้องตัดสินแยก)

1. **Concat host** — ตาม `decisions/ADR-032-concat-host-2026-11-07.md` (ratify option 1 → **amended 2026-11-07: Option 2 EXTRACT สำเร็จ + handshake verified; render ยังไม่ proven**) — config ไม่ได้แก้ใน task นี้
2. **LEGACY** — **FIX ทั้ง 8 แถว (F1–F8) APPLY แล้ว 2026-11-07 (CEO-ordered)** — ดูตาราง FIX ด้านบน; **DELETE ไม่มี**; `scripts/content_render.py` เป็น flag เท่านั้น (ห้ามลบ)
3. **ARCHITECTURE** — เติม 5 ส่วน targeted (ไม่ rewrite) ตามตารางด้านบน

## References

- `central_bus/content/ceo-phase4-kickoff-20261107_20261107T051623810915Z.md` — kickoff (ข้อ 2/3)
- `decisions/ADR-032-concat-host-2026-11-07.md` — Concat host decision (deliverable A)
- `docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md` — product direction (2026-11-01)
- `docs/ARCHITECTURE.md` — assessed doc (last updated 2026-09-27)
- `axis_mcp/departments/content_service.py` + `content_mcp.py` + `media_service.py` — lifecycle/gate/media code (KEEP)
- `tests/test_content_mcp.py:334-345` — 16+ tools catalog (current count reference)

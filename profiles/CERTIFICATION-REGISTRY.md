# 📋 Certification Registry — บันได 4 ด่าน (D0–D4)

> **ผู้ผลิต ≠ ผู้ตรวจ** — อัปเดตโดยผู้ตรวจ/CEO เมื่อผ่านด่านจริงเท่านั้น (rules/06-certification.md, SOP-06)
> **สถานะ ณ 25 ต.ค. 2569: content-creator-sek ตัวแรกผ่าน D1+D2 แล้ว (D3 กำลังทำ) — อีก 19 แผนกยังไม่ผ่านด่านใด — แม่แบบสำหรับผู้ผลิตครั้งแรก**
> **ครั้งแรกที่บันไดถูกเดินจริงจนถึง D2** — ใช้เป็นแม่แบบให้แผนกอื่นได้

## สถานะปัจจุบัน

| Agent | D1 | D2 | D3 | D4 | หลักฐานล่าสุด | หมายเหตุ |
|-------|:--:|:--:|:--:|:--:|:-------------|:---------|
| **content-creator-sek** (content) | **✅ ผ่าน** | **✅ ผ่าน** | ⏳ กำลังทำ | ☐ | `bus/evidence/2026-10-25/d2-content-creator/` · แผน D3: `docs/certification/D3-content-creator-PLAN.md` | **ผ่าน D1 + D2 ครบ (25 ต.ค. 2569)** — ตัวแรกขององค์กร<br>① **D1 ✅** rev.3 (106 บรรทัด) — Owner อนุมัติ 2026-10-25, ไม่มีการแก้เงื่อนไข · ข้อห้ามที่ยังไม่ถูกบังคับในโค้ด (D1 §4) ถูกยกระดับเป็นงาน D2 ครบ<br>② **D2 ✅** `content_agent.py` 144 บรรทัด เรียก tool จริง (read_file ×4, write_file, run_command) · ผู้ตรวจอิสระ `scripts/verify_d2_content_agent.py` = **6/6 ✅ PASSED exit 0** กับโค้ดวันนี้ (sha `0b78009…`) · หลักฐาน `verify-run1/2.{log,json}` + `tool-calls-verify.jsonl` + draft 1479/1558 chars<br>③ **D3 ⏳** มี runner 20 เคส (`scripts/d3_content_creator_eval.py`) — ยังไม่รัน · แผนอยู่ที่ `docs/certification/D3-content-creator-PLAN.md`<br>⚠️ ระหว่างทางเจอ P0 องค์กร: `llm_provider` ตายทั้งระบบ (opencode v2.1.4 ถอด `--pure` + default agent ขอ tool permission) → แก้แล้ว 868 passed
| **team-mcp-builder** (NetEng) | **✅ ผ่าน** | **✅ ผ่าน** | ☐ | ☐ | `bus/evidence/2026-10-26/ffmpeg-skill-mcp-builder-d2-authored.json` · independent rerun: `bus/evidence/2026-10-26/ffmpeg-skill-mcp-builder-d2-independent.json` | **ผ่าน D1 + D2 (26 ต.ค. 2569)** — D1: `docs/certification/D1-content-ffmpeg-integration.md`; D2 mini-agent 150 บรรทัด เรียก MCP initialize/tools/list และ read-only `check` จริง; ผู้ตรวจอิสระ rerัน exit 0. ขอบเขตนี้ยังไม่รับรองการเรนเดอร์สื่อหรือ bridge implementation |
| **product-produck** (Product) | **✅ ผ่าน** | **✅ ผ่าน** | **✅ ผ่าน** | ☐ | `axis_mcp/departments/product_mcp.py` (141 บรรทัด) · `tests/test_product_mcp.py` (5 passed exit 0) · D3 `scripts/d3_product_eval.py` **20/20 PASS exit 0** (`bus/evidence/2026-11-09/d3-product/`, sha-pinned) | **ผ่าน D1+D2+D3 (9–10 พ.ย. 2569)** — ตัวแรกขององค์กรที่จบ D3 · D1 option A standalone · D2 MCP 4 tools ไม่เรียก LLM + guard ครบ (Owner เซ็น 9 พ.ย.) · D3 20 เคส deterministic ผ่านทั้งหมด ไม่ cherry-pick; Thai-only title → invalid_title เป็น known limitation เปิด D2 รอบถัดไป (Owner เซ็น D3 10 พ.ย.) |
| **legal-tulya** (Legal) | **✅ ผ่าน** | **✅ ผ่าน** | ☐ | ☐ | `axis_mcp/departments/legal_mcp.py` (131 บรรทัด) · `tests/test_legal_mcp.py` (5 passed exit 0) | **ผ่าน D1+D2 (10 พ.ย. 2569)** — D1: `docs/certification/D1-legal.md` (standalone, 4 tools, hard stop ไม่ approve); D2 MCP 4 tools ไม่เรียก LLM, ทุก output มี `requires_human_review: true`, guard traversal/invalid/empty ครบ, writes ลง `legal_vault/reviews/` (gitignored) · Owner เซ็น 10 พ.ย. |
| ทุก Department Head + Specialist ที่เหลือ | ☐ | ☐ | ☐ | ☐ | — | ยังไม่ผ่านด่านใด — ห้ามรับงาน execution จริงโดยไม่มีแผน D2 แนบในงาน · **แม่แบบที่ใช้ได้: content-creator-sek และ team-mcp-builder (D1+D2)** |

## ขอบเขตที่ content-creator-sek รอการยืนยัน (ยังไม่อนุญาตเต็มขอบเขต)

> ⚠️ **D0 = ห้ามรับงาน execution จริง** — ยังไม่ผ่าน D2 → อนุญาตได้แค่ "ร่าง/เตรียม" เท่านั้น
- ⛔ ห้ามรับงาน execution จริง (ผลิตคลิปส่งลูกค้า) จนกว่าจะผ่าน D2
- ✅ เตรียมสเปก + ตรวจสเปก + ทดลองกับเครื่องมือในเครื่อง
- ❌ ยัง**ไม่**คิดเนื้อหาเอง (เขียนสคริปต์/เลือกหัวข้อ) — ต้องได้บรีฟจาก CMO หรือ CEO
- ❌ ยังไม่ผ่าน D3 (ตาราง eval ≥20 งาน) — จึงยังรับงานที่ซับซ้อน/ความเสี่ยงสูงไม่ได้

> ⚠️ **บทเรียนจาก PR #19:** fork หนึ่งประกาศว่า agent ผ่าน D2 แล้ว พร้อมชี้ไปที่ไฟล์หลักฐานที่**ไม่มีจริงใน repo**
> → ทุกครั้งที่มีการอ้างด่าน ต้องตรวจว่าไฟล์หลักฐานอยู่ใน repo จริง (ดู `git ls-files bus/evidence/`) ไม่ใช่แค่ลิงก์

## กฎการใช้งาน

1. **D0 = ห้ามรับงาน execution จริง** (เขียนโค้ด/ใช้เครื่องมือ) — งาน execution ต้องแนบ "D2 test" ของ agent นั้นไว้ในงานก่อน
2. **ชิ้นงานแรกของทุก agent = mini-agent ของตัวเอง (D2)** — 50–150 บรรทัด เรียกเครื่องมือเองได้
3. อัปเดตสถานะเมื่อผ่านด่านจริง + แนบหลักฐานที่ `bus/evidence/`
4. หลักฐานย้อนหลัง: `bus/evidence/`, `decisions/`, `brain/session-log.md`

## วิธีอ่าน

- ☐ = ยังไม่ผ่าน (default)
- ✅ = ผ่าน + หลักฐานตรวจแล้ว (ผู้ตรวจ ≠ ผู้ทำ)
- ด่านที่ผ่านแล้วไม่ใช่ "ตลอดกาล" — ถ้า agent พฤติกรรมเปลี่ยน (เช่น fabrication) ให้รีวิวใหม่

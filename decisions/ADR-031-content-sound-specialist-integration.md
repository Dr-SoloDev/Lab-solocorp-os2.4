# ADR-031: Sound Designer เป็น specialist ภายใน Content Creator

**วันที่:** 2026-11-02
**สถานะ:** Accepted — ทำตามคำสั่ง Owner
**เกี่ยวกับ:** ADR-030 (Content MCP boundary) · PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0 (standalone department MCP)

---

## บริบท

`audio-designer-sound` (ซาวด์) อยู่ใน roster ของทีม Content Creator อยู่แล้ว แต่การติดตั้งมี `sound-studio` เป็น MCP/module แยก ทำให้ client เห็นเป็นคนละแผนกและเรียก workflow ข้าม server เพื่อส่ง SFX เข้า Concat การวางลำดับ script, cue sheet, SFX, render, audio review และ approval จึงขึ้นกับ agent/client มากเกินไป

## การตัดสินใจ

1. `audio-designer-sound` คงเป็น specialist ของ Content Creator ตาม `profiles/INDEX.md`; ไม่สร้างแผนกหรือหัวหน้า Sound แยก
2. ย้าย Earshot lookup, SFX render และ final audio review ไว้ใน Content Creator MCP ผ่าน `media_service.py` และลบ adapter `sound_mcp.py` ที่ซ้ำซ้อน
3. เอา `sound-studio` ออกจาก module registry และ client MCP configuration ทั้ง Codex และ OpenCode; Earshot executable ยังคงเป็น dependency ภายในของ Content MCP
4. Concat campaign ใช้ลำดับ: script ล่าสุด → cue sheet ของ script นั้น → SFX ที่ผูกกับ script/cue ล่าสุด (ถ้าต้องใช้) → Concat render → Earshot review ของ MP4 และ checksum ล่าสุด → Publish Gate สำหรับ version หลัง QA → human approval ของ version เดียวกัน
5. การบันทึก approval ไม่ได้ publish อัตโนมัติ; สิทธิ์/แหล่งที่มาและข้อ gate ที่ไม่ผ่านยังต้องให้มนุษย์พิจารณา
6. Campaign ที่ไม่ใช้ Concat ยังคงใช้ Content workflow เดิมได้; เงื่อนไข Earshot QA นี้เริ่มบังคับเมื่อมี Concat render

## เหตุผล

- Sound เป็นความเชี่ยวชาญย่อยในกระบวนการผลิตเนื้อหา ไม่ใช่เจ้าของงานหรือแผนกที่มี lifecycle แยก
- การใช้ MCP เดียวลด handoff ระหว่าง client และทำให้ Content เป็นเจ้าของ campaign, artifact, version และ approval gate ตลอดสาย
- การตรวจ dependency และ checksum กันการใช้ cue sheet/SFX เก่าหรืออนุมัติ render คนละไฟล์กับที่ตรวจเสียง
- Earshot ยังคงแยกเป็นเครื่องมือภายใน จึงไม่เปลี่ยน protocol ระหว่างแผนกหรือขอบเขต standalone ของ Content Creator MCP

## ผลกระทบ

- Client ที่โหลด `sound-studio` อยู่ต้อง reload/restart MCP host จึงจะเห็น Content tools แทน connection เดิม
- การเรียก tool เสียงผ่าน module ID `sound-studio` สิ้นสุดลง; ให้เรียก tools `sound_*` ผ่าน `content-creator`
- Audit และ Bus artifacts ก่อนวันที่ตัดสินใจยังเป็นประวัติเดิม ไม่ถูกเขียนทับหรือลบ
- Production readiness ของ Concat/Earshot runtime ยังคงต้องอาศัย runtime verification และ certification ตาม `rules/06-certification.md`

## References

- `profiles/INDEX.md` — specialist roster ของ Content Creator
- `solocorp_mcp/departments/content_mcp.py` · `content_service.py` · `media_service.py`
- `config/module-registry.json` · `.codex/config.toml` · `opencode.json`
- `docs/runbooks/CONTENT-LOCAL-MEDIA-RENDER.md` · `docs/MEDIA-TOOLKIT.md`

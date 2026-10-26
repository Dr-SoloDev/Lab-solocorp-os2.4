# MCP Department Servers — Content Creator Pilot

## เป้าหมาย

สร้างรูปแบบที่ผู้ใช้เลือกเสียบ MCP server เฉพาะแผนกที่ต้องการได้ทันที โดยแต่ละ server มีหัวหน้าเป็นประตูรับงานและซ่อนรายละเอียดการทำงานของ specialist ไว้ภายในแผนก

ระยะนำร่องนี้ครอบคลุมสองชิ้น:

1. `central-bus` — MCP infrastructure สำหรับจัดเก็บและอ่าน payload ของแผนก
2. `content-creator` — MCP department server ของเสก สำหรับสร้างร่างคอนเทนต์ สคริปต์วิดีโอ visual prompt และตรวจ Publish Gate

## สถาปัตยกรรม

```text
OpenCode V2 / Codex
        │ เลือกต่อ MCP server ที่ต้องการ
        ├── central-bus       (โครงสร้างข้อมูลกลาง)
        └── content-creator   (หัวหน้าเสก → specialist ภายใน)
                                  │
                                  └── shared bus store
                                      central_bus/content/
```

`bus_store.py` เป็น domain-neutral library ที่ทั้งสอง server ใช้ร่วมกัน ส่วน MCP เป็น protocol adapter เท่านั้น จึงไม่ผูก business logic กับ client รายใดรายหนึ่ง

## ขอบเขต Content Creator

- หัวหน้าแผนก: เสก (Content Creation)
- specialist ภายใน: Copywriter, Visual Creator, Video Editor, Trend Scout
- tools ที่เปิดให้ client เรียกผ่านหัวหน้า:
  - `content_department_info`
  - `create_content_draft`
  - `create_video_script`
  - `design_visual_prompt`
  - `review_publish_gate`
- resource: `solocorp://content/sop`

ทุก output เป็นไฟล์ใน `central_bus/content/` และคืน JSON สรุปผลกับ path ของ artifact เพื่อควบคุมขนาด context

## เกณฑ์ผ่าน

- [x] มี shared bus store พร้อม path guard และ atomic write
- [x] Central Bus MCP ลงทะเบียน tools `submit`, `fetch`, `list`
- [x] Content Creator MCP ลงทะเบียน tools และ SOP resource
- [x] Publish Gate ตรวจ redaction + R1–R5 และไม่เผยแพร่อัตโนมัติ
- [x] OpenCode config ต่อได้ทั้งสอง server
- [x] Codex config ต่อได้ทั้งสอง server
- [x] มี unit tests สำหรับ storage, path safety และ content tools
- [x] ทดสอบ stdio handshake จริงจาก MCP client ใน environment นี้

## วงรอบตรวจสอบ

หลังแต่ละรอบให้ตรวจตามลำดับ: import → unit tests → server tool listing → stdio smoke test → ตรวจ `git diff` และสถานะไฟล์ที่สร้างใน bus

## Source audit ของ Content Creator

- `profiles/15-content-creator/SOUL.md` สืบมาจาก commit `3be15da` และมีการขยายตัวตน/ภารกิจใน `5d2e74b`; working tree เดิมสะอาด จึงไม่ต้อง rollback
- `workers/agents/content_agent.py` เริ่มใน `53cae41` และมีการแก้ edge case ของ input เสียใน `9815824`; เก็บเวอร์ชันปัจจุบันไว้เพราะมี test รองรับ แม้ hash จะต่างจาก D2 snapshot เดิม
- `solocorp_skills/creator.py` เป็นกติกา Creator Kit เดิม และ `solocorp_skills/redact.py` เป็นแหล่ง Publish Gate; Content MCP เรียกใช้ gate เดิมแทนการสร้างกฎซ้ำ

## Verification record

- Targeted MCP + Content tests: **11 passed**
- Full suite: **959 passed, 123 warnings**
- Auto-QA gate: **PASS**, coverage **75.4%** (threshold 9%)
- OpenCode `mcp list --pure`: `central-bus` และ `content-creator` = **connected**
- Codex `mcp list --json`: ลงทะเบียน `central-bus` และ `content-creator` = **enabled**

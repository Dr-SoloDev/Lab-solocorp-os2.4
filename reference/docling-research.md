# Docling — เจาะลึก repo (CEO research, 2026-09-25)

> ที่มา: Owner เจอ repo `docling-project/docling` — สนใจทำเครื่องมือจัดการเอกสาร
> วิธีตรวจ: GitHub page + releases API + pyproject.toml + web research (Thai OCR)

## Repo health (สด ณ 25 ก.ย. 2026)
- Stars 67.9k / Forks 4.9k / Issues open 807 / PRs open 124 / Commits 1,489
- Release ล่าสุด v2.130.0 (22 ก.ย. 2026 — 3 วันก่อน), ออกถี่ ~สัปดาห์ละครั้งโดยบอต (docling-ops[bot])
- License MIT, อยู่ใต้ LF AI & Data Foundation, เริ่มโดย IBM Research Zurich
- Status classifier: Production/Stable — ไม่ใช่ของเล่น
- มี AGENTS.md/CLAUDE.md + skills สำเร็จรูป (.agents/.claude/.codex/.opencode/skills) — เป็นมิตรกับ coding agents

## สถาปัตยกรรม (สำคัญ: มัน modular)
- Base `docling-slim` เบา ~50MB (8 packages) → เติม extras ตามต้องการ
- Bundle `standard` = pdf + models-local + rapidocr + office + web + latex + email + iwork + chunking + cli
- `pip install docling` = ตัวเต็ม; Python >= 3.10 (เลิก 3.9 ตั้งแต่ 2.70.0) — เครื่องเรา 3.12.3 ✅
- ของหนักอยู่ใน extras: torch/transformers/onnxruntime (models-local), easyocr, whisper (audio)
- `all` ไม่รวม video (ต้องมี C compiler) — ต้องติดแยกถ้าจะใช้

## ฟีเจอร์ใหม่ที่น่าสนใจ (กันยายน 2026)
- Parsing วิดีโอ (MP4/AVI/MOV/MKV/WebM) + keyframes + transcript
- Chart understanding (bar/pie/line → ตาราง/โค้ด + คำอธิบาย)
- XBRL financial reports (!!) — เกี่ยวกับงาน CFO โดยตรง
- Email (.eml/.msg), ODF, EPUB, Apple Pages/Keynote, MHTML, RTF, AFP
- VLM presets 15+ ตัว รวม SmolDocling (เบา รัน CPU/edge ได้) และ Mineru 2.5 Pro (v2.130.0)
- MCP server + docling-serve (API service, image ที่ quay.io) + integrations (LangChain, LlamaIndex, CrewAI, Haystack, Label Studio)

## ภาษาไทย — คำตอบคือ "ได้ แต่ต้องเทสต์"
- EasyOCR มี thai model (`Reader(['th','en'])`, GPU/CPU ได้) — Docling เลือก engine ผ่าน EasyOcrOptions + ตั้ง lang ได้
- Tesseract มี `tha.traineddata` (ใช้ผ่าน tesserocr extra)
- Layout/TableFormer เป็นโมเดลภาพ ไม่ผูกภาษา — ตารางบิลไทยควรได้โครงถูก เหลือแค่ความแม่นตัวอักษร
- ⚠️ ฟอร์มไทยเฉพาะทาง (ใบกำกับภาษี, บัตรประชาชน) ไม่มีรีวิวยืนยัน — ต้อง spike ด้วยเอกสารจริง

## เข้ากับเครื่อง solocorp-main ไหม
- ✅ Python 3.12, RAM 16G (ว่าง 11G), รัน CPU-only ได้ (onnxruntime), air-gapped ได้หลัง prefetch โมเดล (`docling-tools models download`)
- ⚠️ ช้าหน่อย (ไม่มี GPU): ไฟล์ละหลายวินาที–หลักสิบวินาทีถ้าเปิด layout+table+ocr พร้อมกัน
- ⚠️ ดาวน์โหลดครั้งแรก ~1-2GB (layout, tableformer, ocr) + torch หนัก — ลง HDD (/data) อย่าลง SSD
- ⚠️ ออก release ถี่ — pin version ตอน deploy (`docling==2.130.0`)

## ความเชื่อมกับของเรา
- Papernova (ขาออก: สร้างเอกสาร→PDF) + Docling (ขาเข้า: อ่านเอกสาร→ข้อมูล) = loop ครบ
- ความรู้กระจัดกระจาย (ADR/SOP/session-log) → ย่อยเข้า RAG ได้
- งานที่ต่อได้: สัญญา (@legal-tulya), บิล/งบ (@cfo-meetoo), ใบเสร็จร้าน POS

## แผน spike ที่เสนอ (R&D Lab, 1-2 ชม.)
1. venv ใหม่บน /data → `pip install "docling[standard]"` (pin 2.130.0)
2. เทสต์ 3 ไฟล์จริง: บิลร้าน (สแกนไทย) + สัญญา 1 ฉบับ + ใบกำกับภาษี
3. วัด: ความถูกภาษาไทย / โครงตาราง / เวลาต่อหน้า (CPU)
4. ตัดสินใจ: ใช้เป็น library, ขึ้น docling-serve, หรือพัก

## สถานะ
- [x] Research เสร็จ (2026-09-25)
- [x] ติดตั้งเสร็จ (2026-09-25 ~20:00) — Owner ไฟเขียว "ลุย"
  - venv: `/data/venvs/docling-spike` (Python 3.12.3, docling 2.130.0 + standard bundle, 6.2G — บน HDD)
  - cache: `/data/cache/{pip,huggingface,torch}` (3.1G — หนี SSD สำเร็จ, SSD ไม่โดน)
  - verify: `import docling → 2.130.0` + `docling --help` (convert/convert-remote) ✅
- [ ] ขั้นต่อไปตาม Owner: วางแผนร่วมกัน — ใช้มันยังไง ที่ไหน ยังไง เมื่อไหร่ ตอนไหน (เทสต์เอกสารจริง 3 ใบ: บิลร้านสแกน + ใบกำกับภาษี + สัญญา)

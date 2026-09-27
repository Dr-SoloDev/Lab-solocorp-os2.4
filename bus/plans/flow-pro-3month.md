# Flow Pro 3 เดือน — แผนเตรียมพร้อม (ยังไม่ซื้อ)

> Owner: ซื้อเมื่อระบบ+workflow พร้อม — Pro ฿189×3 (ปกติ 750)
> เป้าหมาย: Google Flow = เครื่องเจนหลัก สร้างตัวตน TH + ทั่วโลก

## สิทธิ์ Pro (ก.ย. 2026, official)
- เครดิต: **50/วัน + 1,000/เดือน** (ไม่ทบ) + ซื้อเพิ่มได้ + upscale 1080p
- ราคาเจน: Veo Lite 8s=10 / Fast 8s=20 / Quality 8s=100 / **Omni 720p 10s=15** / 360p 10s=7
- ของแถมที่ใช้: Notebook high access (แทน ingest บางส่วน), Gemini 3.1 Pro, 5TB, YT Premium Lite

## คณิตเครดิตของเรา (ท่อนละ 10s → Omni 720p = 15)
- ต่อเดือน ≈ 1,000 + (50×30) = **~2,500 = ~166 คลิป 10s = ~15 EP (11 ท่อน)**
- เหลือเฟือสำหรับ pilot + batch — แต่เจนเสียบินเครดิตฟรี (คนบ่นเยอะ) → gate+validator เราคือเกราะ

## flowkit (clone ศึกษาแล้วที่ /tmp/flowkit)
- สถาปัตย์: Python agent :8100 + SQLite + worker ←WS :9222→ Chrome extension ←signed tab→ flow.google.com (batchexecute)
- ห้าม headless — รันบนเครื่อง Owner (มี google-chrome แล้ว ✅)
- skills ~30 (`fk-create-project/gen-images/videos/refs/narrator/pipeline/doctor/...`) + dashboard + tests
- ข้อควรระวัง: unofficial (หักมาแล้วรอบ ก.ย.), cookie/reCAPTCHA หมดอายุ, `FLOW_PROJECT_ID` ต้องสร้างมือ, 3 ฟีเจอร์ยัง unported (upscale 4K, Veo r2v, start+end chain)

## สะพาน SoloCorp → flowkit (งาน Phase 2)
- `scripts.md` (schema v2) → converter → fk-create-project + scenes API
- **เพิ่มฟิลด์ EN visual**: Veo รับ prompt ภาษาอังกฤษเท่านั้น — ทุกท่อนต้องมี `ภาพEN:` คู่ `ภาพ:` (งานของ skill script-design)
- ปก: Nano Banana ผ่าน flowkit (ถูกกว่าเจนวิดีโอ) — เทียบราคาเครดิตวันเริ่ม

## Checklist วันเริ่ม Pro (Day-1)
1. [ ] ซื้อ Pro 189 → เปิด Flow UI ยืนยัน 50 daily + 1,000 monthly
2. [ ] สร้าง project ใน Flow UI → copy UUID → `FLOW_PROJECT_ID`
3. [ ] Clone flowkit จริง + `setup.sh` + venv (ห้ามใช้ /tmp)
4. [ ] Load extension (developer mode) + ล็อกอิน flow.google.com + เปิดแท็บค้าง
5. [ ] Start agent :8100 → เช็ค extension connected → `fk-doctor`
6. [ ] Test: 1 รูป + 1 คลิปสั้น (Omni 360p ถูกสุด) → จดเครดิตจริงที่ใช้
7. [ ] Pilot EP: สคริปที่ validator ผ่าน + Owner gate แล้วเท่านั้น

## กฎเหล็ก 3 เดือน (cfo)
- pilot 1 ท่อนก่อน batch เสมอ / hard cap รีเจน 2 รอบต่อตอน
- นับ cost per published episode ตั้งแต่ EP แรก
- หมดเดือนที่ 3 ทบทวน: ต่อ / หยุด / ย้าย Veo API ทางการ

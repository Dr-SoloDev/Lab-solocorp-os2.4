# SoloCorp OS — Origin Story 10 × 10s

> **Format:** 9:16 vertical, 1080×1920, 30 fps
> **Duration:** 100 seconds (10 episodes × 10 seconds)
> **Audio target:** EBU R128, -16 LUFS, true peak ≤ -1.5 dBTP
> **Lifecycle:** client_generated; provenance is client supplied and unverified
> **Publication:** review_required; human approval required

## Episode Storyboard

| Time | Visual scene | Voiceover / Audio |
|:--|:--|:--|
| 0-10s | EP01 จุดเริ่มต้น 02:52 — นาฬิกาดิจิทัลแสดง 02:52 และวันที่ 15 มิถุนายน 2026; จุดกำเนิดของโปรเจกต์บน Lenovo Z580 | VO: "ตีสองห้าสิบสองบน Lenovo Z580 คือจุดเริ่มต้นของ SoloCorp OS" |
| 10-20s | EP02 เครื่องตั้งต้น — ภาพแล็ปท็อป schematic วางบนโต๊ะทำงาน; เน้นเริ่มจากสิ่งที่มี ไม่แต่งรายละเอียดสเปกเครื่อง | VO: "Lenovo Z580 คือจุดตั้งต้นจากของที่มี เพื่อสร้างระบบให้คนเดียวทำงานได้เป็นทีม" |
| 20-30s | EP03 ทำไม AI ต้องมี CEO — แผนผังบทบาท AI หลายตัวเชื่อมสู่จุดกำหนดทิศทางและเจ้าของผลลัพธ์ | VO: "เมื่อ AI มีหลายบทบาท ใครคุมทิศ? เราวาง CEO ไว้ดูเป้าหมายและความรับผิดชอบ" |
| 30-40s | EP04 ผังองค์กร — การ์ดแผนกเรียงเป็นระเบียบ แสดง 18 หัวหน้าแผนกตามผังองค์กรใน README | VO: "ผังแสดงหัวหน้า 18 แผนก พร้อมผู้เชี่ยวชาญที่รับผิดชอบงานตามบทบาท" |
| 40-50s | EP05 Central Bus — เส้นทางข้อมูลเชื่อมหลายแผนก แยก Control Layer จาก Data Layer | VO: "Central Bus แยกชั้นควบคุมออกจากชั้นข้อมูล ให้ทุกแผนกส่งต่องานได้ชัดเจน" |
| 50-60s | EP06 Content Creator — หัวหน้าแผนกประสานทีมเขียนบท ภาพ เสียง และวิเคราะห์ผ่าน workflow เดียว | VO: "ทีมคอนเทนต์เริ่มเป็น pilot รวมงานเขียนบท ภาพ เสียง และวิเคราะห์ไว้ใน workflow เดียว" |
| 60-70s | EP07 MCP สองตัว — แสดง bus_mcp รับส่งข้อมูลกลางคู่กับ content_mcp ที่เปิดเครื่องมือของแผนก | VO: "เอ็มซีพีสองตัวช่วยแยกหน้าที่ ตัวหนึ่งส่งข้อมูลกลาง อีกตัวเปิดเครื่องมือคอนเทนต์" |
| 70-80s | EP08 Human Approval Gate — เช็กลิสต์ Publish Gate ค้างสถานะ review_required; ห้ามแสดง approved | VO: "AI ช่วยสร้าง แต่ Publish Gate รอมนุษย์ตรวจและอนุมัติก่อนเผยแพร่" |
| 80-90s | EP09 จาก prototype สู่ OS — เส้นเวลาไปยัง SoloCorp OS 2.4 พร้อมป้าย pre-release | VO: "SoloCorp OS เวอร์ชัน 2.4 ยังเป็น pre-release เราทดสอบต้นแบบอย่างเปิดเผย" |
| 90-100s | EP10 มาร่วมสร้าง — ภาพประภาคารและทางรถไฟสื่อการเดินทางร่วมกัน พร้อมชื่อ SoloCorp OS | VO: "ถ้าคุณสร้างสิ่งต่าง ๆ ด้วยตัวเอง มาร่วมทดลองและพัฒนาไปด้วยกัน" |

## Production Notes

- Visuals are original synthetic Three.js scenes; they are not historical footage.
- Voice uses the installed Thai Piper model for internal review only; its model card is non-commercial.
- The local synth bed is a placeholder. Clear replacement music before public use.
- User-supplied origin date/time and Lenovo Z580 detail remain independently unverified.
- Keep the Publish Gate at review_required until a human reviews the rendered file and records approval.

## Source References

- User-supplied Origin brief: 02:52, 15 June 2026, Lenovo Z580; independently unverified.
- README.md and LICENSE: organization facts, v2.4 pre-release status, and project MIT license.
- profiles/INDEX.md and profiles/15-content-creator/SOUL.md: department and specialist roles.
- solocorp_mcp/departments/content_service.py and content_mcp.py: Content workflow and approval gate.

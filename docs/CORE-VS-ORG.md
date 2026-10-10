# Core vs Organization Design — เส้นแบ่งของ SoloCorp OS

> Owner-approved (AAAA ชุดที่ 1): เขียนเส้นลง docs ก่อน ไม่แยก repo ไม่แตกงาน
> ที่มา: วิสัยทัศน์ L2 (ฐานอิสระ) / L3 (Org OS) + หลักการ 3 ข้อ (อย่าบังคับให้ทุกคนเป็น SoloCorp / ออกแบบอิสระโดยไม่เริ่มจากศูนย์ / ดูเหมือนได้ ≠ พิสูจน์ว่าได้)

## นิยาม 1 ประโยค

- **Core = กลไกที่ทำให้ agent ทำงานร่วมกันได้อย่างน่าเชื่อถือ** — ไม่รู้ว่าองค์กรหน้าตาเป็นอย่างไร ห้ามแตก ห้าม fork แล้วเปลี่ยนพฤติกรรม
- **Organization Design = สิ่งที่แต่ละคนออกแบบเอง** — โครงสร้าง บทบาท กฎ วิธีบริหาร แตกได้เต็มที่ ขอแค่เรียก Core ผ่าน interface เดียวกัน

## อะไรอยู่ฝั่งไหน

| Core (ห้ามแตก) | Org Design (แตกได้) |
|:---------------|:--------------------|
| `central_bus/` — queue, state, router, qa_gate, bus_tags, db, audit, health | `profiles/` — 20 dirs, SOUL.md, team specialists, routing.yaml |
| `loop_runner/` — scheduler, loops, verdict_log, state | `skills/@solocorp/` — 9 canonical skills |
| `bus/` runtime contract — queue/evidence/verdicts/audit formats | `decisions/` ของแต่ละทีม, GTM/content ของตัวเอง |
| `rules/`, `sop/` — กติกาพฤติกรรม + วิธีปฏิบัติ | ชื่อแผนก จำนวนแผนก โทนเสียง ภาษา |

## กฎเหล็ก 3 ข้อ

1. **Core ห้าม import Org** — Org import Core ได้ฝ่ายเดียว ใครฝ่าฝืน = รีวิวไม่ผ่าน
2. **Core ไม่รู้จักชื่อแผนก** — ไม่มี `cfo`, `changful`, `18 แผนก` ในโค้ด Core มีแค่ `agent_id`, `workstream`, `trace_id`
3. **พฤติกรรม Core เปลี่ยนต้องมี ADR + เทส** — Org เปลี่ยนแค่แก้ SOUL.md/routing ได้เลยไม่ต้องขอ

## จุดผิดที่รู้แล้ว (ต้องย้าย ไม่ใช่ลบทิ้ง)

- `workers/evidence_collector.py` อยู่ใน `workers/` แต่ทำหน้าที่ Core (verify) — ทางแก้: ย้ายเข้า Core หรือผูกเป็น interface ทางการ ห้ามให้ Org เรียก implementation ตรง (งาน follow-up ของ send-back loop)

## อะไร "ไม่ใช่" งานนี้ (non-goals)

- ไม่แยก repo / ไม่แยก package / ไม่เปลี่ยน import path ใดๆ รอบนี้
- ไม่แตะ Cost enforcement (เสาอ่อนสุด — design only แยกอีกงาน)
- ไม่เปลี่ยนพฤติกรรม runtime ใดๆ — docs ล้วน

## เชื่อมกับ 7 เสา L3

Core รับผิดชอบเสา 2 (State), 3 (Policy), 5 (Verification), 6 (Recovery), 7 (Observability) ส่วนเสา 1 (Organization) กับ 4 (Cost policy) เป็นของ Org Design ที่เรียก Core อีกที ช่องใหญ่สุดที่ต้องทำต่อคือ **send-back loop (5→6)**: ตรวจไม่ผ่านแล้วงานต้องมีสถานะ "ส่งกลับพร้อมเหตุผล + นับรอบ" อย่างเป็นทางการ — งานถัดไป

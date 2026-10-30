# สำเร็จแล้ว จริงหรือ? — V2

**Duration:** 63 seconds
**Status:** Internal review draft; synthetic demonstration only; not a report of real incidents.
**Source:** `scripts/media/model_health_v2.json`
**Visual:** Original deterministic Canvas2D UI animation at 1080×1920, 30fps, with persistent label “ตัวอย่างจำลอง”.
**Timing:** Voiceover cues follow measured individual phrase audio. Captions are phrase-timed, not word-aligned.

| Timestamp | Scene | Voiceover |
|:--|:--|:--|
| 0–9s | status — สำเร็จแล้ว / จริงหรือ? | VO: "หน้าจอขึ้นว่าสำเร็จ แต่งานเสร็จจริงหรือยัง? ลองดูว่าไฟเขียวนี้ยืนยันอะไร" |
| 9–19s | split — รับงานแล้ว / ยังไม่ใช่คำตอบ | VO: "ระบบอาจรับงานเข้าคิวแล้ว แต่โมเดลยังไม่ส่งคำตอบกลับมา สองสถานะนี้ต้องตรวจแยกกัน" |
| 19–31s | probe — ลองเรียกจริง / ตรวจคำตอบด้วย | VO: "ตรวจชื่อผู้ให้บริการกับชื่อโมเดล ส่งคำขอทดสอบหนึ่งครั้ง แล้วตรวจว่าคำตอบตรงกับที่คาดไว้หรือไม่" |
| 31–41s | evidence — เก็บหลักฐาน / ให้ตามกลับได้ | VO: "เก็บทั้งชื่อโมเดล เวลา และคำขอ พร้อมคำตอบ หรือรายละเอียดเมื่อเกิดข้อผิดพลาด ให้คนอื่นเปิดตรวจซ้ำได้" |
| 41–52s | alert — เรียกไม่ได้ / ต้องมองเห็น | VO: "ถ้าเรียกไม่ได้ ให้แสดงข้อผิดพลาดตรง ๆ แจ้งเจ้าของงาน พร้อมหลักฐานที่ตามกลับได้ แล้วตรวจซ้ำหลังแก้ไข" |
| 52–63s | question — ขอดูหลักฐาน / ก่อนเชื่อผล | VO: "ความน่าเชื่อถือเริ่มจากผลที่ตรวจได้ วันนี้ เอเจนต์ของคุณมีหลักฐานอะไร ให้คนอื่นตรวจซ้ำได้บ้าง?" |

All displayed provider, model, request, response, and timestamps are fictional. The test result “ตอบกลับได้” only means the sample request got the expected short response; it is not proof of full task correctness. Voice model is Piper th_TH-tsync2-medium, CC-BY-NC-SA-3.0, non-commercial use only. Human rights review and approval are required before publication.

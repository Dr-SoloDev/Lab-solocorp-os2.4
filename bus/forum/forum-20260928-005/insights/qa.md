# qa @ forum-20260928-005

QA มองแผนนี้แล้วเห็น 2 เรื่องที่ต้องมี gate ก่อน EP.4 จะออก

จุดดี: มี Owner review gate อยู่แล้วตรงจุดที่ถูก — generation เป็นส่วนที่คุณภาพ "พังเงียบ" มากที่สุด (เสียงพูดผิด, subtitle ลอย, ภาพไม่ตรงสคริปต์) ถ้า gate อยู่ก่อนเจน ก็ตัด loss ตรงนั้นได้ และ pipeline ที่ ingest จาก repo เองคือ deterministic พอที่จะเขียน regression test รอบ output ได้

จุดเสี่ยง: เดือนแรกผลิตจริง 4+ คลิปด้วย ffmpeg ต่อ master + ปก + โพสตามแพลตฟอร์ม = จุดที่พังบ่อยที่สุดและจะไม่เจอตอน dev เทสต์ (codec/เสียงหาย, safe-area ปกโดนตัดตามแพลตฟอร์ม, aspect ratio ผิด) ผมอยากได้ golden-file test ตั้งแต่ EP.1 — เก็บ hash/ขนาด

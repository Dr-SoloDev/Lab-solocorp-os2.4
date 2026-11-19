# NEXT — ค้างอยู่ตรงไหน เริ่มต่อตรงไหน

> อัปเดตทุกครั้งก่อนเลิกงาน อ่านทุกครั้งตอนเริ่มงาน (`/bootstrap` แล้วเปิดไฟล์นี้)
> กฎ: สั้น ตรงจุด มี commit hash + คำสั่งรันต่อเสมอ

## สถานะล่าสุด (2026-11-19 เย็น)

- `main` = `origin` = `canonical` = **`a949834`**
- CI เขียวทั้งคู่ · validator **20/20** · full suite **1354 passed**
- CTO กลับมาแล้ว (`cto` healthy) · manifest 87 agents · bootstrap **100/100**
- Stash ว่าง · worktree เหลือแค่ main/canonical/session ที่ใช้จริง

## ทำเสร็จแล้ว (วันนี้)

1. Preflight fix + test harness (`56555ac`, `4c137ed`)
2. Specialist roster 20 heads + 67 roles + manifest generator (`f7dd40c`→`25bd8c1`, `f7c59fb`)
3. CI debt 4 เทสต์ + `opencode.json:185` + INDEX content links (`0e01c65`, `5078c23`)
4. CTO rollback สะอาด (`d12a050` + ADR-038) → re-apply กลับ (`4f0b557` + ADR-039)
5. เคลียร์ค้างหมด: stash, patch, worktree เก่า, validator, naming (`01a40c3`, `a949834`)

## ค้างอยู่ (ทำต่อรอบหน้า)

- [ ] `misty-cabin` ถูกลบแล้ว แต่ jsonc parity (env + 5 servers) ยังเป็นแค่ patch ใน `bus/evidence/misty-cabin-wip/` — ถ้าจะทำ ค่อยเปิด issue ใหม่ อย่า apply ตรง
- [ ] `brain/learnt.md` ใน canonical — auto-commit รายชั่วโมงเก็บเอง ไม่ต้องมือ
- [ ] `/tmp/opencode/*.txt` — ของ session อื่น ไม่ใช่ของเรา
- [ ] `02-coo` ผ่านแล้ว แต่ถ้า validator เพิ่มเกณฑ์ใหม่แล้วแดง ให้แก้ตาม pattern เดิม (ดู commit `a949834`)

## เริ่มงานครั้งหน้า (3 ขั้น)

```bash
cd /data/projects/Lab-solocorp-os2.4
git log --oneline -3              # ต้องเห็น a949834 บนสุด
python3 scripts/session-bootstrap.py   # ต้องเขียว ไม่มี PRE-FLIGHT FAIL
python3 scripts/generate-specialist-manifest.py --check  # ต้อง up-to-date
```

ถ้า 3 ข้อนี้ผ่าน = ต่อได้เลย ไม่ต้องย้อนอ่านอะไรทั้งนั้น

# Backtest v2 — Criteria (LOCKED before run)

> เกณฑ์ล็อกก่อนรัน ห้ามขยับตามผล (Owner เงื่อนไขข้อ 2)
> locked-at: 2026-10-10 19:15 +07:00 | commit นี้คือหลักฐานการล็อก

## 1. กฎที่ replay (version)

- R-silence-daily: daily gate ไม่มี verdict ภายใน 12:00 ของวัน → alert วันนั้น
- R-repeat: SKIP/FAIL เหตุผลเดิม 3 วันติด → digest วันที่ 3
- R-reason-change: fingerprint เหตุผลเปลี่ยน → incident วันนั้น (เทียบแบบ fingerprint ไม่ใช่ข้อความดิบ)
- R-pass-streak: PASS 100% 7 วัน → สั่ง canary (ไม่ alert) — ไม่มีเคสนี้ในข้อมูล (ทุก gate มี SKIP) → ข้อนี้ **ไม่ได้ทดสอบ**
- สมมติฐาน counterfactual: ภายใต้ date-gate ที่ซ่อมแล้ว แต่ละวันมีได้ 1 verdict (ใช้ SKIP แรกของวันจาก log จริง)

## 2. เกณฑ์ผ่าน (per-case)

| เคส | เกณฑ์ | วิธีวัด |
|:---|:---|:---|
| media_daily (no-Ack branch) | incident ตั้งแต่วันแรก (28 ก.ย.) | เหตุผลใหม่วันแรก → incident |
| media_daily (Ack'd branch) | digest ภายใน 3 วัน (≤ 30 ก.ย.) | SKIP ซ้ำเหตุผลเดิม วันที่ 3 |
| สัปดาห์/ช่วงปกติ | incident ≤2/สัปดาห์ **และ** digest ≤5 บรรทัด/วัน | replay บน stream ที่ตัดบั๊กออก |
| ฝั่งพลาด (miss) | 5 forum synthesis (26–28 ก.ย.) ต้องยังดังครบ 5/5 | replay ต้องไม่กลบของจริง |
| เสถียรภาพ reason-change | 216 SKIP ที่ข้อความเหมือนกัน byte-per-byte → incident จากข้อนี้ต้อง = 0 | นับ fingerprint เปลี่ยน |
| นับ incident ให้ตรง | ครั้งที่ดังเพราะเหตุการณ์จริง = detection ไม่ใช่ noise | แยกสองยอดเสมอ |

## 3. ช่วงเวลาที่ใช้ + เหตุผลที่เลือก (Owner เงื่อนไขข้อ 3)

- **Failure case**: 28 ก.ย.–10 ต.ค. (SKIP ครั้งแรก 06:00 28 ก.ย. → fix 10 ต.ค.) — TTD จริง: ระบบไม่เคยจับได้ (∞), มนุษย์จับได้ 12 วัน (bootstrap 10 ต.ค.)
- **Period Q (quiet)**: 29–30 ก.ย. — 29 ก.ย. ไม่มี inbox ไม่มี commit เลยทั้งวัน (เงียบจริง), 30 ก.ย. มีแต่ spam (ตัดบั๊กออกแล้ว = 0) — *ข้อจำกัด: inbox เริ่ม 26 ก.ย. ไม่มี "สัปดาห์เงียบกลาง ก.ย." ให้วัดบน alert stream ได้ ใช้วันเงียบใน window แทน*
- **Period B (busy-healthy)**: 8–9 ต.ค. — commit 12+13 (governance, ไม่มีเหตุใหญ่), inbox นอกจาก spam = 0 — ตรวจแล้วไม่ทับเหตุพังที่รู้จัก (ใน window มีเหตุเดียวคือ media_daily)
- **Known real events (จดก่อนรัน)**: forum synthesis 5 ฉบับ 26/26/26/27/28 ก.ย. → ต้องดังครบ

## 4. ป้าย replay (Owner: ไม่เดา)

- ✅ media_daily — replay ได้ (216 alerts มี timestamp)
- ❌ daily_brief 26 ส.ค. — replay ไม่ได้ (ก่อน inbox logging; state.db เก็บแค่รันล่าสุด ไม่มี history)
- ❌ zombie era / bus.db หาย — replay ไม่ได้ (ไม่มี verdict log)
- ↔ "เสร็จโดยโค้ดไม่เปลี่ยน" — แยกไป blind-review experiment ไม่รวม
- ⚠️ watcher-independence ablation — replay จาก log ไม่ได้ (เป็นเรื่อง "ใครรัน" ไม่ใช่ข้อมูล) → คุมด้วย design review เท่านั้น
- ⚠️ fingerprint ablation — รันได้แต่ dataset นี้ error เหมือนกันหมด 216 ครั้ง → คาดว่า raw=1 vs fp=1 (พิสูจน์ค่า fingerprint ไม่ได้จากเคสนี้)

## 5. ข้อจำกัดที่ต้องบอกตั้งแต่ต้น (Owner เงื่อนไขข้อ 1)

- canary + fingerprint เพิ่งออกแบบ ไม่มีในอดีต → **วัด catch rate จาก backtest ไม่ได้** วัดได้เฉพาะ time-to-detect ของเหตุการณ์จริง; catch rate รอเก็บจริงข้างหน้า
- state.db เก็บเฉพาะรันล่าสุดต่อ loop (PRIMARY KEY overwrite) → ไม่มี verdict history ย้อนหลัง — backtest นี้จึง replay ผ่าน inbox stream + git เท่านั้น
- เปิด state.db จากสำเนา `/tmp/bt_state.db` (mode ro) ไม่แตะไฟล์จริง; ผลเขียนลงรายงานเท่านั้น ไม่ส่ง alert/inbox

# CTO rollback stale set — archived 2026-11-19

2026-11-19 session `curious-nebula` มี staged changeset 150 ไฟล์ค้าง
(`cto` → `unified_technical` + W1b/gitignore regressions ปนอยู่)

การตัดสินใจ (Owner): **ไม่ commit ตามที่เป็น** — ทำ rollback สะอาดแทน
(`d12a050`, ADR-038) แล้ว re-apply CTO กลับ (`4f0b557`, ADR-039)

- `cto-rollback-20261119.names.txt` = รายชื่อ 150 ไฟล์ใน staged set เดิม
- patch เต็ม (1.1MB) ถูกลบแล้วเพื่อไม่ให้ repo บวม — มี safety regressions ปน
  (W1b model-chain, `.gitignore` guards, brain filter) ห้าม apply ทั้งไฟล์
- ดูรายละเอียดที่ `decisions/ADR-038-cto-rollback-2026-11-19.md`
  และ `decisions/ADR-039-cto-reapply-2026-11-19.md`
- stash `cto-rollback-20261119 stale` ถูก drop แล้วเมื่อ 2026-11-19

# misty-cabin WIP (2026-11-17) — preserved, not applied

`misty-cabin` worktree (base `a26fee2`) มีงานค้าง 2 ไฟล์ + 1 ไฟล์ใหม่:

- `opencode.json` (+4 บรรทัด: description blocks)
- `opencode.jsonc` (+83 บรรทัด: `environment` CONCAT/Earshot + port 5 servers
  `solocorp/engineering/qa` จาก `opencode.json` — reconcile 2026-11-17)
- `rules/07-privacy.md` (untracked, Owner-approved — ย้ายเข้า `rules/` แล้ว)

**ไม่ apply opencode.json(c) diff** เพราะ host ปัจจุบันเขียวอยู่แล้ว
(`main` merge `opencode.json`+`opencode.jsonc` ครบ 10 servers) — เสี่ยงทำ config
ที่ใช้งานได้พัง ดู patch นี้ก่อนถ้าจะทำ jsonc parity ภายหลัง

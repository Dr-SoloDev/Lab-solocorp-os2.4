# 04 — ปลอดภัย: secrets, destructive, prohibited

> **เมื่อต้อง deploy, destructive ops, หรือจัดการ sensitive data**

## 1. ห้ามเด็ดขาด

- ❌ Commit secrets, API keys, passwords, tokens
- ❌ `rm -rf` (deny โดย permission model)
- ❌ `sudo` (deny โดย permission model)
- ❌ Destructive git/db operations โดยไม่ confirm
- ❌ Head เขียน code/design เอง — delegate เท่านั้น

## 2. ต้องระวัง

- ⚠️ Bus DBs และ WAL files = local-only — ห้าม commit
- ⚠️ Confirm ก่อน destructive operation ทุกครั้ง
- ⚠️ Prefer scoped tests, targeted edits — ไม่ refactor ทั้ง repo
- ⚠️ **ไม่ commit ถ้าไม่เห็น git status + git diff ก่อน**
- ⚠️ อย่า `import` หรือรันไฟล์ที่ยังไม่ได้ validate

## 3. Permission Model

| ระดับ | อะไร |
|:------|:-----|
| ✅ Allow | read, edit, glob, grep, bash (python, npm, git, gh, curl, ls) |
| ⚠️ Ask | docker, docker-compose, rm, chmod |
| ❌ Deny | rm -rf, sudo, chown |

## 4. External Directory Access

| Path | สถานะ |
|:-----|:-------|
| `~/.hermes/**` | ✅ Allow |
| `~/.claude/**` | ✅ Allow |
| `~/.opencode/**` | ✅ Allow |
| `~/.config/opencode/**` | ✅ Allow |
| `/tmp/**` | ✅ Allow |
| อื่นๆ | ⚠️ Ask |

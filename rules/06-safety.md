# 🛡️ Safety — อะไรห้ามทำ?

## ห้ามเด็ดขาด

- ❌ Commit secrets, API keys, passwords
- ❌ `rm -rf` (deny โดย permission)
- ❌ `sudo` (deny โดย permission)
- ❌ Destructive git/db operations โดยไม่ confirm

## ต้องระวัง

- ⚠️ Bus DBs และ WAL files = local-only (ไม่ commit)
- ⚠️ Confirm ก่อน destructive operation
- ⚠️ Prefer scoped tests, targeted edits — ไม่รีแฟกเตอร์ทั้ง repo
- ⚠️ ไม่ commit ถ้าไม่เห็น git status + git diff ก่อน

## Permission Model (opencode.json)

| ระดับ | อะไร |
|:------|:-----|
| Allow | read, edit, glob, grep, bash (python, npm, git, gh, curl, ls) |
| Ask | docker, docker-compose, rm, chmod |
| Deny | rm -rf, sudo, chown |

## External Directory Access

| Path | Status |
|:-----|:-------|
| `~/.hermes/**` | ✅ Allow |
| `~/.claude/**` | ✅ Allow |
| `~/.opencode/**` | ✅ Allow |
| `~/.config/opencode/**` | ✅ Allow |
| `/tmp/**` | ✅ Allow |
| อื่นๆ | ❌ Ask |

# Worktree MCP Contract — กันแดงซ้ำถาวร

> Owner: @architect-songsak (AXIS Architect) | Date: 2026-11-18 | Status: ACTIVE  
> Hotfix base: `3c382aa fix(mcp): use absolute venv path for worktree` | Worktree: `curious-nebula`

## 1. ปัญหาที่เกิด (Root Cause — ทำไมแดง 6 ตัว)

`curious-nebula` แดง 10 → 4 เขียว / 6 แดง เพราะ 3 ปัจจัยซ้อนกัน:

| # | ปัจจัย | รายละเอียด |
|---|--------|-------------|
| 1 | **`.venv` หายใน worktree** | `git worktree add` ไม่ copy `.venv` (ignored) → ไม่มี python ให้ spawn MCP |
| 2 | **relative path ใน opencode config** | `opencode.json(c)` ใช้ `.venv/bin/python3` แบบ relative → resolve ต่อ `session cwd` |
| 3 | **session cwd ≠ worktree root** | OpenCode session cwd = `/home/drsolodev` ไม่ใช่ `/.../curious-nebula` → `/.venv` หาไม่เจอ → `NotFound` spawn |

ผล: `12 generations` ค้าง (6 ตัว stale) ก่อน hotfix; หลัง `symlink + absolute path + restart --yes` → `6 current` เขียว `10/10`.

Evidence hotfix (`3c382aa`):

```
.venv -> /data/projects/Lab-solocorp-os2.4/.venv   (symlink ใน worktree)
opencode.json:  5 servers .venv → absolute (/data/projects/.../.venv/bin/python3)
opencode.jsonc: 3 servers .venv → absolute
restart-mcp --yes: 12 stale → 6 current, 10 MCP green (verified 2026-11-18 21:13)
```

## 2. กฎใหม่ (Contract — ทุก worktree ต้องทำ)

> **ห้ามสร้าง worktree แบบ manual `git worktree add` อย่างเดียว — ต้องผ่าน contract นี้**

1. **ทุก worktree ต้องมี `.venv` symlink** → `ln -s /data/projects/Lab-solocorp-os2.4/.venv .venv` (absolute target เท่านั้น ห้าม relative ห้าม copy)
2. **ทุก `opencode.json` / `opencode.jsonc` ต้องใช้ absolute python path** → `/data/projects/Lab-solocorp-os2.4/.venv/bin/python3` ห้าม `".venv/bin/python3"` หรือ `"./.venv/..."` แม้แต่จุดเดียว
3. **`session-bootstrap.py` ต้องเขียว** → `.venv` check + config check ผ่านก่อนเริ่มงาน (fail = exit 2 + แดง)
4. **Verify ก่อนส่งงาน** → `scripts/restart-mcp.sh` (dry-run) ต้อง `stale=0`, `opencode mcp list` ต้อง `10/10 connected`

## 3. วิธีสร้าง worktree ที่ถูกต้อง

### ทางที่ถูก (บังคับ)

```bash
scripts/worktree-setup.sh <path> <branch>   # สร้าง + symlink + verify ครบในคำสั่งเดียว

# ตัวอย่าง
scripts/worktree-setup.sh /home/drsolodev/.local/share/opencode/worktree/27bed3/my-feature feat/my-feature

# ถ้า path มีอยู่แล้วแต่ขาด symlink
scripts/worktree-setup.sh --fix-only        # ซ่อม worktree ปัจจุบัน
```

สคริปต์ทำ:

1. `git worktree add <path> -b <branch>` (หรือ attach ถ้า branch มีอยู่)
2. `ln -s /data/projects/Lab-solocorp-os2.4/.venv <path>/.venv` (skip ถ้ามีแล้วและถูกต้อง)
3. ตรวจ `opencode.json(c)` ไม่มี `".venv/bin/python3"` เหลือ (grep absolute)
4. `python scripts/session-bootstrap.py` → ต้องไม่มี `🔴 MCP PRE-FLIGHT`
5. `bash scripts/restart-mcp.sh` → แสดง `stale` count

### ทางที่ผิด (ห้าม)

```bash
git worktree add /tmp/my-wt -b feat/x   # ❌ ขาด .venv → MCP แดงทันที
# แล้วไปแก้ opencode.json ด้วยมือเป็น ".venv/bin/python3"  → ❌ relative ห้าม
```

## 4. วิธีตรวจ (Verification Checklist)

รันจาก worktree root:

```bash
# 1. symlink ต้องชี้ถูก
ls -la .venv
# → lrwxrwxrwx ... .venv -> /data/projects/Lab-solocorp-os2.4/.venv
test -x .venv/bin/python3 && echo "venv OK" || echo "venv BROKEN"

# 2. config ต้อง absolute เท่านั้น
! grep -q '"\.venv/bin/python3"' opencode.json opencode.jsonc && echo "config OK (absolute)" || echo "config FAIL (relative left)"
grep -c '/\.venv/bin/python3' opencode.json opencode.jsonc

# 3. bootstrap ต้องเขียว
python scripts/session-bootstrap.py
# → ต้องไม่มีบรรทัด "🔴 MCP PRE-FLIGHT FAIL"
# exit code 0 = เขียว, exit 2 = แดง (pre-flight fail)

# 4. MCP ต้อง current ไม่มี stale
bash scripts/restart-mcp.sh
# → generations: X   stale: 0   target: X   + "DRY RUN — nothing killed."

# 5. MCP list ต้องเขียวครบ
opencode mcp list
# → 10 บรรทัด ✓ connected (stealth-browser = disabled ไม่นับ), 0 x

# 6. health probe (direct python, ไม่ผ่าน MCP catalog)
 /data/projects/Lab-solocorp-os2.4/.venv/bin/python3 -c "
import asyncio
from axis_mcp.unified_technical.tools.unified_tools import unified_list_tools
asyncio.run(unified_list_tools(None))
# หรือ full health:
# from axis_mcp.unified_technical.modules.* + unified_health_check → status healthy
"
```

**ก่อน commit/push ทุกครั้ง** ให้รันข้อ 1-4; ก่อนรายงาน CEO ให้แนบ output ข้อ 4-5.

## 5. Sync Check — `axis_mcp/unified_technical` vs `axis_mcp/cto`

| ตำแหน่ง | สิ่งที่มี | สิ่งที่ไม่มี |
|---------|----------|--------------|
| **worktree `curious-nebula` (HEAD 3c382aa, detached, base 52689ac)** | `axis_mcp/unified_technical/` (16 files, tracked) | `axis_mcp/cto/` |
| **main repo `/data/projects/Lab-solocorp-os2.4` (feat/cto-phase1-wave1, 12cfe98)** | `axis_mcp/cto/` (16 files, renamed จาก unified_technical ใน 2632f90) | `axis_mcp/unified_technical/` |

Diff: `axis_mcp/unified_technical/server.py` vs `axis_mcp/cto/server.py` = differ (import path + label เปลี่ยนใน Wave1-2).

**สรุป:** worktree นี้ fork ก่อน CTO migration (Wave1-1 `2632f90 git mv unified_technical -> cto`). จึง divergence โดยตั้งใจ — ไม่ใช่บั๊กของ worktree.

**Contract decision (2026-11-18):**

- ❌ **อย่า commit โค้ด `axis_mcp/unified_technical/` จาก worktree นี้เข้า main ตอนนี้** — จะชนกับ `axis_mcp/cto/` บน `feat/cto-phase1-wave1` และย้อน rename
- ✅ บันทึกไว้ใน contract นี้พอ — sync ต้องทำผ่าน `feat/cto-phase1-wave1` branch เท่านั้น เมื่อ CTO Phase 1 merge กลับ main แล้วค่อย rebase worktree
- หากต้องใช้ `unified_technical` health ใน worktree นี้ → ใช้ path เดิม `/data/projects/Lab-solocorp-os2.4/.venv/bin/python3 -m axis_mcp.unified_technical.server` ตาม `opencode.jsonc` (ถูกต้องแล้ว)
- งานถัดไป: หลัง `main` merge CTO แล้ว ให้ `git fetch origin && git rebase origin/main` ใน worktree หรือสร้าง worktree ใหม่ด้วย `scripts/worktree-setup.sh` บน base ใหม่

## 6. Automation & Guardrails

| Guardrail | อยู่ที่ไหน | ทำอะไร |
|-----------|------------|--------|
| `scripts/worktree-setup.sh` | สร้าง worktree | auto symlink + absolute check + bootstrap verify |
| `scripts/session-bootstrap.py` | ทุก session start | pre-flight: `.venv` missing → 🔴 + exit 2; relative path → 🔴 + exit 2 |
| `scripts/restart-mcp.sh` | ก่อน/หลัง แก้ MCP config | dry-run รายงาน stale/current; `--yes` kill stale generations |
| `opencode.json(c)` absolute | config | กัน cwd mismatch ถาวร (ไม่ใช่ hotfix ชั่วคราว) |

Hook แนะนำ (optional, ไม่บังคับเพราะ worktree ไม่มี `.git/hooks` แยก):

```bash
# ใส่ใน ~/.gitconfig หรือ repo hooks ถ้าต้องการเตือนทุกครั้งที่ git worktree add
# ตอนนี้ใช้ doc + worktree-setup.sh เป็น primary guard; hook เป็นเสริม
```

## 7. Incident Timeline

- 2026-11-18 21:07 — พบ MCP แดง 6/10 ใน curious-nebula (`.venv` หาย + relative path + cwd `/home/drsolodev`)
- 2026-11-18 21:13 — CEO hotfix `3c382aa`: symlink + 8 จุด absolute + `restart-mcp --yes` → เขียว 10/10
- 2026-11-18 — Architect แผน A: verify stale=0 + contract + automation + pre-flight + sync check (commit นี้)

## 8. References

- `scripts/worktree-setup.sh` — สร้าง worktree ที่ถูกต้อง
- `scripts/session-bootstrap.py` — pre-flight checks (`.venv` + absolute path)
- `scripts/restart-mcp.sh` — stale detection (`runtime.restart_required` logic)
- `opencode.json` / `opencode.jsonc` — MCP servers `command` ต้อง absolute
- ADR-017 — free-tier subagent gate (ไม่ใช่สาเหตุรอบนี้ แต่เกี่ยวข้องกับ MCP lifecycle)
- `decisions/ADR-032-concat-host-2026-11-07.md` — ตัวอย่าง host-specific MCP caveat (เทียบเคียง)

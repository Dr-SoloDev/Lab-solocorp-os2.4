# SoloCorp OS 2.4 — Grok Project Rules

@rules/INDEX.md

---

SoloCorp OS rules อยู่ที่ `rules/` — เปิด `rules/INDEX.md` สำหรับ 30-sec scan

Platform-specific notes:

- Grok subagents: `.grok/agents/` → spawn ด้วย `subagent_type`
- Slash skills: `/pipeline`, `/handoff`, `/status`, `/audit`, `/deploy`, `/brain`, `/route`
- Max subagent depth: **1** (child ไม่มีลูก)
- ใช้ `explore` สำหรับ read-only research
- File-mutating experiments: ใช้ `isolation: worktree`

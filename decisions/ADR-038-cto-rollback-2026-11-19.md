# ADR-038 — CTO Wave1 Rollback → `unified_technical` (2026-11-19)

| รายการ | รายละเอียด |
|:-------|:-----------|
| **Status** | Accepted — Owner decision 2026-11-19 |
| **Supersedes** | ADR-036 (CTO Phase 1 / Wave 1 migration) |
| **Scope** | rename + MCP config + routing rules + docs/profiles/skills/agent |
| **Commit** | this commit (rollback) — pre-rollback state: `f7c59fb` |

## 1. Context

ADR-036 renamed `axis_mcp/unified_technical/` → `axis_mcp/cto/`, added the
`cto` MCP server (`axis_mcp.cto.server`), the `@cto` routing alias, the CTO
profile/skills/agent, and the CTO migration evidence. The live environment and
the Specialist Manifest v1.1 were built on that state.

A parallel staged changeset (150 files) was a full rollback of the migration.
Owner decision: roll back cleanly to `unified_technical`, but **keep the safety
fixes and evidence** that the staged rollback also reverted.

## 2. Decision

Roll back the CTO Wave1 **code/config/rules/docs** only:

- `axis_mcp/cto/` → `axis_mcp/unified_technical/` (rename + import/DB/label revert)
- remove `axis_mcp/departments/cto_mcp.py`; revert `engineering_mcp.py` / `qa_mcp.py` references
- remove the `cto` MCP entry from `opencode.json`; `opencode.jsonc` → `unified-technical`
- `rules/01-receive.md`: `@cto` → `@architect-songsak` / `@changful` / `@qa`
- remove `profiles/cto/`, `.opencode/agents/cto.md`, `skills/@axis/cto/`; remove the CTO section from `profiles/INDEX.md`
- README: Unified Technical wording
- regenerate `docs/SPECIALIST-MANIFEST-v1.0.md` (86 agent files; `cto.md` removed)

## 3. Explicitly kept (NOT rolled back)

| ไฟล์ | เหตุผล |
|:-----|:-------|
| `workers/llm_provider.py` + `tests/test_model_health.py` | W1b model-chain fix (default model missing alert / cache isolation) |
| `.gitignore` guards (`owner_footage_staged_*`, `legal_vault/reviews/*`) | raw owner footage 100+ MB และเอกสารกฎหมายส่วนตัวเคยเสี่ยงหลุด |
| `tests/test_brain_auto_commit_filter.py` + `loop_runner/loops/brain_auto_commit.py` | filter กัน brain auto-commit กวาดไฟล์ผิด |
| `bus/evidence/cto-migration/**`, `bus/dispatch/confirmations/CTO-*` | หลักฐาน migration — เก็บไว้เป็น audit trail |
| `central_bus/content/**`, `bus/media/creator/**` | artifact ของ owner — ไม่เกี่ยวกับ rollback |
| `decisions/ADR-036`, `ADR-037`, `ADR-030` | ประวัติการตัดสินใจ — ไม่ลบ |

## 4. Consequences

- MCP namespace กลับเป็น `unified-technical` (`architect_*` / `engineering_*` / `qa_*` / `unified_*` ไม่เปลี่ยนชื่อ)
- `@cto` routing ถูกถอด; กลับไปใช้ `@architect-songsak` / `@changful` / `@qa`
- CTO profile/skills/agent ไม่อยู่ใน tree ปัจจุบัน (ยังอยู่ใน git history)
- ต้อง restart MCP หลัง merge เพื่อให้ config ใหม่มีผล
- Specialist Manifest = 86 agent files (unlisted: `axis-ceo`)

## 5. Rollback plan (re-apply CTO Wave1)

1. `git revert <this commit>` (หรือ restore จาก `f7c59fb`) — ได้ `axis_mcp/cto/`, `cto` MCP, `@cto`, CTO profile/skills/agent กลับมา
2. ตรวจ `opencode.json` / `opencode.jsonc` ว่าชี้ `axis_mcp.cto.server`
3. `scripts/restart-mcp.sh` (dry-run → `--yes`) แล้ว `opencode mcp list`
4. ยืนยัน health (`unified_technical_health` ผ่าน cto server) และรัน `python3 scripts/generate-specialist-manifest.py --check`
5. หลักฐาน CTO migration ยังอยู่ที่ `bus/evidence/cto-migration/**` — ไม่ต้องกู้

> หมายเหตุ: patch `/tmp/opencode/cto-rollback-20261119.patch` เป็น snapshot ของ
> staged changeset เดิม (มี safety regressions ปนอยู่) — ใช้เป็น reference เท่านั้น
> ห้าม apply ทั้งไฟล์

## 6. Verification (ของ commit นี้)

- `python3 scripts/generate-specialist-manifest.py --check` → up-to-date
- `pytest tests/ central_bus/tests/` → 1354 passed, 1 skipped
- `python3 scripts/session-bootstrap.py` → MCP pre-flight OK (venv + config absolute)
- หลัง restart: `opencode mcp list` → `unified-technical` connected

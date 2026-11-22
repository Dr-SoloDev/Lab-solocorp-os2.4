# SoloCorp OS — Codex CLI Pipeline Commands

> Output templates for the 6 pipeline skills. Paste into your Codex prompt to get structured responses.
> Note: Codex agents are auto-generated from `profiles/`. These templates document expected output format.

---

## `/pipeline <feature>`

**Trigger:** "รัน pipeline สำหรับ \<feature\>"

**Output template:**

```markdown
# Pipeline Result: <feature>

## Routing
- Primary dept: ...
- Owner: ...
- Secondary depts: ...

## Work done
- [Dept] — [what was done] — [artifacts]

## Tests / evidence
- Command: `...`
- Result: pass/fail
- Coverage: ...

## Handoffs
| From | To | Task | Status |
|------|----|------|--------|
| ... | ... | ... | done/blocked |

## Open blockers
- ...

## Next actions for Owner
- ...
```

---

## `/handoff <from> <to> <task>`

**Output template:**

```markdown
## Handoff Record — [from] → [to]

**Pipeline ID:** [id]
**From:** [Dept/Agent]
**To:** [Dept/Agent]
**Timestamp:** [ISO8601]

**Context:** [สรุปสั้นๆ ว่าเกิดอะไรขึ้นมาก่อน]

**Deliverables:**
- [file/link]

**Explicit Request:** [สิ่งที่ต้องการให้ทำต่อ — ชัดเจน วัดผลได้]

**Known Issues:** [อะไรที่ยังไม่สมบูรณ์]

**Deadline:** [เวลา]

**Escalation:** ถ้ามีปัญหา → Orchestrator (พี่วุฒิ)
```

---

## `/status`

**Output template:**

```markdown
# SoloCorp Status

| Component | State | Detail |
|-----------|-------|--------|
| Central Bus :8099 | up/down | version, uptime |
| govctl API :8765 | up/down | ADR/RFC/Guard counts |
| Queue | active | depth, offsets |
| Projects | n active | names |
| Loop Runner | running/idle | last run |

## Notes
- ...

## Recommended next actions
- ...
```

---

## `/audit [scope]`

**Output template:**

```markdown
# Audit Report — [scope]

**Scope:** [all / dept / pipeline-id]
**Checked at:** [timestamp]

## Events (last 50)
| Time | Type | Source | Detail |
|------|------|--------|--------|

## Anomalies
- ...

## Compliance summary
- Guards active: N
- Violations: N
- Recommendation: ...
```

---

## `/deploy`

**Output template:**

```markdown
# Deploy Report

## Profiles exported
- [dept] → [path] — ok/error

## Config validation
- opencode.json: valid/invalid
- .grok/config.toml: valid/invalid
- .codex/config.toml: valid/invalid

## MCP servers
- [name]: reachable/unreachable

## Gaps
- ...
```

---

## `/brain <context>`

**Output template:**

```markdown
# Brain Note — [timestamp]

**Session:** [id]
**Project:** [slug under bus/projects/]

**Context saved:**
[summary of session state, decisions made, next steps]

**Written to:** `bus/projects/<slug>/brain-<ts>.md`
```

---

## `/route <request>`

**Output template:**

```markdown
# Route

| Field | Value |
|-------|-------|
| Primary dept | ... |
| Head | ... |
| Codex agent | `XX-dept-head` |
| Secondary | ... |
| Suggested next | /pipeline or direct implement |

## Why
- ...

## Next command
- `...`
```

---

## Notes for Codex CLI

- Agents in `.codex/agents/` are auto-generated from `profiles/` via `scripts/export-codex-agents.py` — do not edit manually.
- To update agent prompts, edit the source `profiles/NN-dept/SOUL.md` and re-run the export script.
- `AGENTS.md` at repo root is also read by Codex CLI for project context.
- Project MCP: `solocorp` + `stealth_browser` — see `.codex/config.toml`.

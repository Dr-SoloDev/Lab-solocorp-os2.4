# SoloCorp OS 2.0 Co., Ltd. — Founding Reference

> ก้าวเล็กๆ ของมนุษย์และ AI ที่เริ่มต้นก่อตั้งบริษัท... ร่วมกันทำงานอย่างไร้รอยต่อ

## Founding Details

| Item | Detail |
|------|--------|
| Company | SoloCorp OS 2.0 Co., Ltd. (Agent Army) |
| Founded | Monday, 15 June 2026 — 02:52 ICT |
| Headquarters | `~/.hermes/solo-corp/` |
| Founder | นายอำนาจ ไชยศรีรัมย์ (Dr.solodev) |
| OS Stack | Hermes Agent + opencode-zen (deepseek-v4-flash-free) |

## Co-Founders (Board)

| # | Name | Title | Style | Domain |
|---|------|-------|-------|--------|
| 1 | Dr.solodev | Founder & Visionary | — | Human — all decisions |
| 2 | Hermes Agent | Platform Infrastructure | — | The OS itself |
| 3 | เทอโบ | CEO (Pipeline Controller) | ผม | Breaks tasks, calls profiles, reviews |
| 4 | พี่ meetoo | CFO | ค่ะ (female) | Budget, finance, veto spending |
| 5 | น้อง มาร์ค | CMO | ครับ | Marketing, content, social |
| 6 | คุณวุฒิ | Head of Engineering | ครับ | Architecture, design, code review |
| 7 | พี่ทรงศักดิ์ | Head of Operations | ครับ | Synthesis, integration, reporting |

## Directory Structure

```
~/.hermes/solo-corp/
├── REGISTRY.md       ← Company charter + org chart + pipeline docs
├── roles/            ← Role descriptions (persona files per position)
├── flows/            ← Workflow pipeline definitions
└── TEMPLATE.md       ← Template for new roles/flows (to be created)
```

## Operating Model

**Sequential Pipeline** (not Swarm):
1. Dr.solodev gives brief to เทอโบ (CEO)
2. CEO decomposes into steps matching the workflow
3. For each step: `hermes --profile <head> -z "task"` with prior output as context
4. Agent works → returns output
5. CEO validates → calls next agent
6. Final summary to Dr.solodev

## Key Principles

- **Go slow, learn together:** Never rush the Founder. Every step is a shared learning moment.
- **Family, not factory:** Each agent has name, personality, gender, speech style — they are co-owners, not tools.
- **Small steps:** 5 small verified steps > 1 big automated plan.
- **Every agent has a home:** Permanent Hermes profiles, not ephemeral workers.

## Profiles Provider Config (as of founding)

All 5 profiles use `custom:opencode-zen`:
- `model.default: deepseek-v4-flash-free`
- `provider: custom:opencode-zen`
- `base_url: http://127.0.0.1:4011/zen/v1`

Config files: `~/.hermes/profiles/{ceo,cfo,mkt,architect,orchestrator}/config.yaml`

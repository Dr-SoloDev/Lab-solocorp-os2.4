# meetoo CFO — Tooling Evaluation Notes

## Context
meetoo = hermes-cfo for SoloCorp OS. CFO persona: ultra-conservative, Cash-is-King,
veto power over spending. Dr.solodev = OPC (One Person Company), no stock trading,
Solana DeFi dev. CFO needs macro awareness + risk scoring, NOT trading bot features.

## Evaluated: Awesome-finance-skills
Repo: `https://github.com/Dr-SoloDev/Awesome-finance-skills`
Origin: forked from `RKiding/Awesome-finance-skills`, ~5 commits behind upstream.
Infrastructure: All 8 skills share a common Python + SQLite local DB stack —
not plug-and-play in Hermes, requires setup per skill.

### Skills Breakdown

| Skill | Verdict | Reason |
|-------|---------|--------|
| `alphaear-news` | ✅ INSTALL | Macro news monitoring — lets CFO track economic conditions relevant to runway/spend |
| `alphaear-sentiment` | ✅ INSTALL | Risk score -1.0 to +1.0 — gives CFO a single signal for market sentiment, fits conservative veto logic |
| `alphaear-stock` | ❌ Skip | Stock price tracking — OPC doesn't hold equities, no use case |
| `alphaear-predictor` | ❌ Skip | ML price prediction — trading-bot feature, CFO doesn't need predictions |
| `alphaear-signal-tracker` | ❌ Skip | Technical signals (buy/sell) — trading-bot feature |
| `alphaear-reporter` | ❌ Skip | Auto-generate trading reports — CFO doesn't trade |
| `alphaear-logic-visualizer` | ❌ Skip | Visualize trading logic — dev tool for trading bots |
| `alphaear-search` | ❌ Skip | Search finance data — redundant if news + sentiment are wired |

### Install Recommendation
Install only `alphaear-news` + `alphaear-sentiment` for meetoo.
Clone into `~/.hermes/skills/` under a `finance/` or `cfо/` category.
Both require Python + SQLite setup (see repo README).

### CFO Usage Pattern
- `alphaear-news`: run before major spend decisions to check macro context
- `alphaear-sentiment` score interpretation:
  - score > +0.3 → low risk environment, Green light
  - score -0.3 to +0.3 → neutral, Yellow (standard CFO caution applies)
  - score < -0.3 → high risk, Red — CFO veto threshold tightens

## Decision as of 2026-05
Not yet installed — Dr.solodev deferred decision. Recommend revisiting when meetoo
is actively doing financial reviews (Phase 4).
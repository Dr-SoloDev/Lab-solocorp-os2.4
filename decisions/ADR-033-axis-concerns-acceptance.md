# ADR-033 — AXIS Rebrand: Owner Accepts 3-Item Concern Backlog (2026-11-10)

> **Status:** Accepted (Owner signed 2026-11-10) · **L5 direction:** SoloCorp OS → AXIS Framework
> **Context:** 18/19 dept heads polled (2026-11-09, `bus/evidence/2026-11-09/axis-opinions/`), avg support **8.2/10**, no objections, 3 recurring concerns. Owner accepted all 3 as tracked backlog.

## C1 — Backward-compat + rollback for Phase 3 rename (Owner: Engineering/Architect)
- Keep `SOLOCORP_*` env names, `central_bus/`, `opencode.jsonc` filename, evidence/ADRs/archives frozen (already done in `6d76f6e`).
- Still open: E2E regression evidence across all 10 MCPs (pytest 1187 is unit-level only), migration map for external clients, rollback = revert single commit.
- Gate: no "done" claim on the rename until MCP 10/10 green post-restart + E2E pass.

## C2 — Trademark clearance for "AXIS" (Owner: Legal @legal-tulya) — FORMAL REVIEW STILL OPEN
Preliminary web search (2026-11-10, NOT a legal opinion) found the name crowded **in our exact domain**:
- **netlify/axis** — "AXIS Agent Experience Index Score", MIT open source, tests MCP servers, works with OpenCode. Direct domain overlap.
- **AxisWorkflow/axis** — "Axis Workflow™" for AI agents (Claude Code/Codex/Cursor), trademark claimed by Kenneth A. Younge (Swiss filing). Direct competitor + mark claimed.
- **MachinesOfDesire/axis-protocol** — "AXIS Protocol" for agent identity/delegation/authorization; "AXIS"/"AXIS Prime" pending trademarks of Kipple Labs. Direct overlap with our Two-Tier control layer.
- **VirSanghavi/axis** — multi-agent coordination over MCP (AGPL). Same technical space.
- **USPTO Reg. 8201555** — "AXIS" registered (Axis, LLC, IC 009, entertainment software). Different class, still a live US mark.
- **Axis Communications (axis.com)** — famous mark (network cameras/ACAP platform). Famous marks enjoy broad protection.
- Also: AXION Solutions AXIS, myaxis.ai (Belva Digital LLC), axis.bh, goaxis.ai, SureCity AXIS AI gateway.
- **Implication:** full clearance requires formal Legal review (TH + US/EU search, class analysis). Until then: use "AXIS" as working brand only; keep "SoloCorp OS" in legal/copyright notices; do NOT file, publish launch materials, or claim ™.
- Options if clearance fails: (a) keep SoloCorp OS as legal name + AXIS as internal codename, (b) pick a more distinctive name.

## C3 — D3 product-produck sign-off (Owner: checker) — ✅ SIGNED 2026-11-10 ("ผ่าน")
- Harness `scripts/d3_product_eval.py` (20 cases, deterministic, no LLM): **20/20 PASS, exit 0** (2026-11-09, sha-pinned in `bus/evidence/2026-11-09/d3-product/`).
- Known limitation recorded: Thai-only titles → `invalid_title` (ASCII-only slug; future D2 iteration, not a silent bug).
- Owner signed explicitly 2026-11-10. Registry already shows product-produck D1+D2+D3 ✅.

## Accepted backlog (tracked, not closed)
- [x] C1: E2E regression (`docs/certification/E2E-10-MCP-2026-11-10.md`, 9/9) + MCP 10/10 post-restart verify ✅ — เหลือ migration map แยก
- [ ] C2: Formal Legal trademark review (TH/US/EU) before any launch claim (memo เบื้องต้นบันทึกแล้ว: เสี่ยงสูง)
- [x] C3: Explicit D3 product sign-off ✅ (Owner "ผ่าน" 2026-11-10)

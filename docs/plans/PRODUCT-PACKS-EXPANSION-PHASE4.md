# Product Packs Expansion Assessment — Phase 4 (PLAN ONLY)

| Field | Value |
|:------|:------|
| Author | @product-produck, Head of Product |
| Date | 2026-11-07 |
| Parent kickoff | `central_bus/content/ceo-phase4-kickoff-20261107_20261107T051623810915Z.md` (Phase 4: docs/decision only, no renders, no code behavior changes) |
| Frozen scope | `campaign_synth_phase1_20261107` v5, `campaign_synth_phase2_20261107` v7, `campaign_synth_phase3_20261107` v7 — **not touched by this plan** |
| Product line context | v2.4.0 pack line: CFO, Legal, Content Creator (per `README.md:36`, `README.md:255-269`) |
| D-cert status of author | **D0.** `profiles/CERTIFICATION-REGISTRY.md:11-13` records only `content-creator-sek` and `team-mcp-builder` as D1+D2-passed; all other heads/specialists are D0 ("ยังไม่ผ่านด่านใด"). This document is a **D0 plan-only artifact** (no code, no MCP changes, no renders, no PRD edits). It does not claim execution capability. |
| Status | Proposal for Architect / CEO approval. Does not authorize build. |

> **Question asked:** can the Content Creator Phase 1–3 pattern (governed MCP + Central Bus + Publish Gate + local rendering) expand to CFO and Legal?
>
> **Short answer:** Yes for the *governance shell* (standalone adapter + bus storage + gate/human approval + provenance + D-cert ladder). **No** for the *domain core* (media pipeline, R1–R5 publish criteria, campaign lifecycle, approval-override semantics). CFO and Legal each need a new domain core and a new domain gate; cloning Content code will copy the wrong risks. Detail below.

---

## 1. Pattern recap — what exactly is reusable from Content?

The reusable pattern = 6 components. Each is graded **REUSE** (copy mechanism, rename domain) or **DO NOT COPY** (Content-specific).

### 1.1 Standalone department MCP adapter — REUSE

- **Mechanism:** `solocorp_mcp/departments/content_mcp.py:49-62` — `_registry()` seeds **only** `("content-creator",)` on first use and the docstring states importing the module must not touch the filesystem, so a standalone MCP that a host merely *lists* creates no registry file and declares only the module it owns (citing PRD §155 / FR-07). This is the standalone-usability guarantee in code.
- `content_mcp.py:512-526` — `module_registry_status()` is public, read-only, and answers without `SOLOCORP_API_KEY` (CMD-006 §4.2). A department MCP must be inspectable standalone.
- `content_mcp.py:65-99` — FastMCP instructions declare the boundary in plain language: head = client-facing boundary, five specialists internal, drafts store-without-publishing, every publication requires recorded human approval for the current version. CFO/Legal adapters need the same one-screen boundary declaration.
- **Generalization evidence:** the pattern is not Content-only. `solocorp_mcp/departments/engineering_mcp.py:1-22` and `qa_mcp.py:1-41` follow the same shape (head as boundary, specialists internal, small tool surface). They are *thinner* (info + routing/status) than Content — proof the shell generalizes, and proof Content is the only department that has so far implemented the full gate + render stack.
- **PRD anchor:** `docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md:41` (department independence), `:73-79` (§6.1 standalone mode — full capability without Core/CEO/Busd), `:145` (FR-07 standalone compatibility).

### 1.2 Bus data plane (protocol-neutral storage) — REUSE

- **Mechanism:** `solocorp_mcp/bus_store.py:1-6` — "Shared, protocol-neutral storage… MCP servers use this module instead of calling one another… connect to a single department server and still get a working data layer." Domain logic never calls another MCP server directly.
- `solocorp_mcp/departments/content_service.py:45` — `DEPARTMENT = "content"`; `:31-38` imports `fetch_from_bus / submit_to_bus / submit_bytes_to_bus` from `bus_store`. Every artifact write/read goes through the bus (e.g. `:336`, `:2607`, `:2667`, `:2672`, `:2851`). Department directory isolation is enforced by `bus_store.py:45-51` (`_department_dir` rejects path escape).
- **Registry split:** `solocorp_mcp/module_registry.py:3-15` — config (tracked, human-decided) vs state (ignored, runtime-observed) in two files. CFO/Legal must reuse this, not invent a third registry.
- **Task envelope:** `solocorp_mcp/task_tracking.py:1-14, 30, 55-80` — `pending → running → completed/failed/cancelled`, strict `task-<12hex>` validation, `brief` hidden from list by default. Content reuses it with a scope guard: `content_mcp.py:529-620` (`task_create/get/list/update` reject `dept != "content"`). CFO/Legal adapters need the same scoped TaskTracker with `dept="cfo"/"legal"`, `module="cfo"/"legal"`.
- **PRD anchor:** `PRD:153` (NFR — reuse Central Bus where data model fits), `PRD:78` (department data path must be declared; missing dependency must disable the feature explicitly).
- **Reuse rule for CFO/Legal:** one `DEPARTMENT` constant, one scoped TaskTracker, bus-only persistence. **No** cross-department direct calls, no shared department directory.

### 1.3 Gate + human approval (exact-version, never auto-publish) — REUSE mechanism, REWRITE gate criteria

- **Mechanism (Content):**
  - `content_mcp.py:294-303` (`review_publish_gate`) — "without approving it"; `:306-317` (`record_human_approval`) — "for the exact reviewed campaign version."
  - `content_service.py:2653-2691` — `review_publish_gate` returns `status="review_required"`, `approval_required=True`, `publish_action="blocked_until_human_approval"` (`:2690`).
  - `content_service.py:2773-2879` — `record_human_approval` enforces: version must be `vN` (`:2780-2784`), must equal current campaign version or error (`:2790-2793`), must have a review for that exact version or error ("run review_publish_gate for this exact campaign version first", `:2795-2796`), Concat workflow must be `ready_for_human_review` (`:2797-2806`), latest local render must not have failed (`:2807-2810`). Any later asset change bumps version and resets review/approval (`remove_campaign_asset`, `:2694-2770`).
  - `content_service.py:2845` — approval records `"recorded_by": "human MCP caller; identity is not independently authenticated"`. Honest provenance — the approval is a recorded assertion, not authenticated identity.
  - SOP restatement: `content_service.py:2887` (lifecycle), `:2896-2897` ("Failed checks must be resolved; do not treat a report as approval… Any later asset change requires a new review and approval. This MCP does not publish.").
- **Gate criteria (Content-specific, DO NOT COPY):** `solocorp_skills/redact.py:14-19` defines R1–R5 (a verifiable evidence item in every post; one failure + cost; a "not yet done / don't know yet" line; no comparing/measuring others; close with an open question, not a sales CTA). `redact.py:221-276` implements them as text heuristics + redaction patterns (secrets/PII, `:43-60`). These are **editorial criteria for public social posts**. They have no meaning for a budget or a contract review. CFO/Legal need domain gates (proposed in §2/§3). What transfers is the *shape* (automated checks → report artifact on bus → human decides on exact version → approval record on bus), not the checks.
- **Override semantics (DO NOT COPY):** Content allows `overrides_failed_checks` (`content_service.py:2847-2848`, `:2825-2826`) — a human may explicitly approve past failed checks. **Under no circumstances should CFO/Legal copy this.** Money and legal outputs must hard-block on failed evidence/scope checks, or escalate to a higher authority tier (see §2.3/§3.3). An "override and ship" button for numbers or compliance is the exact failure this program exists to prevent.

### 1.4 Provenance honesty (`client_supplied_unverified`) — REUSE

- **Mechanism:** `content_mcp.py:70-71` ("Client-generated artifacts retain client-supplied, unauthenticated provenance; this route never calls an LLM"), `content_service.py:2050-2082` (`ingest_client_generated_artifact` validates provenance + source references, stores `"provenance_status": "client_supplied_unverified"`, `:2078`), SOP `:2888`.
- **Rule for CFO/Legal:** any externally supplied figure, contract text, or client-generated financial/legal artifact must carry `provenance_status: client_supplied_unverified` until independently reconciled. The MCP never relabels client input as verified. For CFO this is the single most important carry-over (see F-gate in §2.3); for Legal it applies to client-supplied contracts and license claims.

### 1.5 D-cert ladder + Maker ≠ Checker — REUSE

- `rules/06-certification.md:14-19` — D1 (1-page note, no code) → D2 (50–150-line agent that really calls tools, with run output + exit code) → D3 (≥20-task eval table: expected vs actual + root cause, no cherry-picking) → D4 (someone else reproduces via runbook). `:23-25` — Maker ≠ Checker every gate; default = NOT PASSED; never skip.
- `profiles/CERTIFICATION-REGISTRY.md:11` — `content-creator-sek` is the template: D1 ✅ (Owner-approved rev.3, 2026-10-25), D2 ✅ (144-line `content_agent.py`, independent verifier `scripts/verify_d2_content_agent.py` = 6/6 exit 0), D3 ⏳ (runner `scripts/d3_content_creator_eval.py` exists, **not yet run**). `:13` — every other head/specialist is D0. `:28` — D0 = must not accept execution work.
- **Implication for expansion:** CFO and Legal are D0 today. No build before their own D1 → D2 → D3 → D4. Content itself is only D1+D2 — cloning its pattern before its D3 eval runs means cloning an unproven gate (see §4).

### 1.6 What is Content-only and must NOT be copied

- Piper/FFmpeg/Concat/Earshot/ElevenLabs stack (`content_mcp.py:225-278, 398-483`; `media_service.py`). Host-specific, media-specific. CFO/Legal have no renderer to clone.
- 6×15-second / 10×10-second script layout, 90-second storyboard default, 1080×1920 (`content_mcp.py:405-418`). Layout is a creative choice, not a pattern.
- Campaign lifecycle states (`scaffold → client_generated → llm_generated → human_edited → review_required → approved`, `content_service.py:2887`) and degraded-render flags (`:2267-2308`). CFO/Legal need domain lifecycles (§2.2/§3.2); `scaffold` itself is a current template-draft state, not legacy (per kickoff `:10`) — do not rename/remove it in Content, and do not import it into new packs where it doesn't fit.
- R1–R5 text heuristics (see §1.3). Domain gates replace them.

---

## 2. CFO pack assessment

### 2.1 What a CFO MCP would do

Today CFO exists as profile text only: `profiles/02-cfo/SOUL.md` (Head meetoo + 3 `team/*.SOUL.md` on disk; SOUL `:263-281` claims 5 specialists — Quinn/Cassandra have no files — a pre-existing count discrepancy to fix in docs, not code) and **no** `cfo_mcp.py` / `cfo_service.py` (the departments directory has `content_*, engineering_mcp, qa_mcp, media_service` only). The pack line (`README.md:261-267`) lists CFO as a pack that "does Budget control · Financial analysis · Audit trail · Tax strategy · FP&A" — that is a profile directory, not a delivered MCP. Do not let the README pack table be read as a capability claim.

A CFO MCP in the Content shell shape would expose, via the Head boundary:

| Tool (proposed) | Domain role | Content analog |
|:----------------|:------------|:---------------|
| `cfo_department_info()` | Head/specialists/scope/data root | `content_department_info` |
| `create_budget_analysis()` | Budget/cost draft artifact from **supplied** figures | `create_content_draft` |
| `ingest_client_figures()` | Store client-supplied numbers with `client_supplied_unverified` | `ingest_client_generated_artifact` |
| `recalculate()` | **Deterministic** re-computation from stored inputs only (no LLM arithmetic) | `render_campaign_media_local` (the "compute" step) |
| `review_numbers_gate()` | Evidence/consistency checks → report artifact | `review_publish_gate` |
| `record_human_approval()` | Human approves exact version + amount tier | `record_human_approval` (no override copy) |
| `task_create/get/list/update_status` | Scoped task tracking | Content task tools |

Specialist mapping (internal, never separate client entry points — same as Content's five): Dana (Bookkeeper/Controller, `01-dana.SOUL.md` — day-to-day accounting, reconciliation, monthly close) = data ingestion + reconciliation; Riley (FP&A Analyst, `02-riley.SOUL.md` — budgeting, rolling forecast, variance analysis) = budget/variance/forecast drafts; Morgan (Financial Analyst) = scenario modeling (deferred, see §2.5); meetoo = boundary + gate owner.

The existing templates are directly mappable to artifacts: Monthly Financial Review (`SOUL.md:154-188`), Capital Request (`:190-218`), 5-Question Decision Framework (`:131-148`).

### 2.2 CFO domain lifecycle (replaces campaign lifecycle)

`scaffold → figures_ingested (unverified) → draft_created → recalculated → gate_reviewed → approved | rejected`. Every transition writes an artifact manifest to `central_bus/cfo/`. Any input change after `gate_reviewed` bumps version and resets review/approval (same reset semantics as `remove_campaign_asset`, `content_service.py:2732-2742`).

### 2.3 Gate = numbers gate (not publish gate) + human approval for numbers

CFO gate checks (draft) — all must pass, no override:

- **F1 — Every figure traces to an input artifact.** Each number in the draft cites a stored `figures_ingested` filename + line. An untraced figure fails the gate. (Analog of R1 "verifyable evidence," but enforced per-figure, not per-post.)
- **F2 — Inputs reconciled.** Supplied figures are cross-checked against source references (invoice, statement, API usage export) where provided; unreconciled inputs stay `client_supplied_unverified` and are visibly flagged (analog: provenance flag, §1.4).
- **F3 — Arithmetic recomputable.** `recalculate()` reproduces every total/variance from stored inputs deterministically; a mismatch fails the gate. LLM-generated numbers that cannot be recomputed are rejected at ingest.
- **F4 — Approval tier respected.** SOUL `:141-148` tiers: < 1,000 THB auto (log only, no artifact decision); 1,000–10,000 CFO; 10,000–50,000 CFO+CEO; > 50,000 CFO+CEO+Owner. `record_human_approval` must reject a tier-2 approval for a tier-3 amount. The MCP recommends; per SOUL `:224` "CFO recommend, CEO/Owner decide" — the MCP **never** approves money by itself.
- **F5 — No invented figures.** If a required input is missing, the tool returns `error: missing_input` with the exact missing item — never a placeholder, estimate, or zero-fill presented as a figure. (Direct analog of Content's "stop on error, never silently skip" rule, `content_mcp.py:81-82`.)

### 2.4 MVP scope vs deferred

**MVP:** budget analysis + monthly review + capital request drafts from user-supplied figures; deterministic recalculation; F1–F5 gate; tiered human approval; full audit trail on bus (`SOUL.md:102` — "Audit Trail บังคับ"); standalone verification in an external client.

**Deferred:** bank/accounting-system connectors (no source-of-truth data feed exists in tree) → MVP must work on supplied figures only, with the unverified flag doing the honesty work; Monte Carlo / DCF / valuation (`SOUL.md:298-311`); tax filing/planning execution (SOUL `:119-122` — draft planning notes only; filing is a regulated act, out of scope); investment recommendations (SOUL `:224-225` already forbids speculative advice — harden into a tool-level rejection); any payment execution (MCP approves *documents*, never moves money).

### 2.5 Risks (CFO-specific)

- **Fabricated numbers presented as analysis** — the highest-severity risk in this program. Mitigation is F1/F3/F5 + `client_supplied_unverified` + D3 numeric eval (≥20 cases with known ground truth; a single invented figure = D3 fail).
- **False precision** — percentages to 2 decimals from unverified inputs. Mitigation: gate requires input-quality label on every output (verified / unverified / estimated — estimated only where the user explicitly supplies an estimate and it is labeled as such).
- **Approval laundering** — recording a human approval the human never gave. Mitigation: same honesty as Content `:2845` (approver_note required, identity unauthenticated, but approval version must match exactly); plus tier enforcement (F4).
- **Tax/compliance advice overreach** — SOUL `:227` already routes legal advice to Legal. MVP tax output = checklist + deadline reminder, never a filing position.
- **Data sensitivity** — financial figures on bus must not leak into public artifacts. Reuse `redact.py` BLOCK patterns for non-financial secrets; financial figures stay in `central_bus/cfo/` and are never returned in list views (same privacy shape as `task_tracking.py:10-12` hiding `brief`).

---

## 3. Legal pack assessment

### 3.1 What a Legal MCP would do

Today Legal exists as profile text: `profiles/13-legal/SOUL.md` (Head ตุลย์) + 3 `team/*.SOUL.md` (Compliance Auditor, Legal Document Reviewer, Client Intake) + `SoloCorp_Profile_Governance_Policy.md`, and **no** `legal_mcp.py` / `legal_service.py`. Pack table (`README.md:264`): "Contract review · License compliance · Risk assessment · Data governance."

Crucially, `profiles/13-legal/tulya/team/02-legal-document-review.SOUL.md:17-24` defines the specialist as **first-pass triage** explicitly: "ไม่ให้คำแนะนำทางกฎหมายขั้นสุดท้ายแทนทนายความ, ไม่ลงนามหรือรับรองเอกสารใดๆ" (`:42-44`). That boundary is what makes an MVP safe. The Legal MCP is a triage + checklist + redline-summary engine, not a law practice.

Proposed tools (Head boundary, specialists internal):

| Tool (proposed) | Domain role | Content analog |
|:----------------|:------------|:---------------|
| `legal_department_info()` | Head/specialists/scope/data root | `content_department_info` |
| `intake_client_matter()` | Client intake draft (per `03-legal-client-intake.SOUL.md`) | `create_content_draft` |
| `ingest_client_document()` | Store client-supplied contract?license, `client_supplied_unverified` | `ingest_client_generated_artifact` |
| `review_document()` | Risk flags (High/Med/Low), missing terms, redline vs prior version | `create_video_script` (the domain "draft") |
| `license_check()` | Dependency license vs MIT compatibility matrix | `review_publish_gate` (partial) |
| `review_legal_gate()` | Scope/disclaimer/evidence checks → report | `review_publish_gate` |
| `record_human_approval()` | Human (Legal head + caller) approves exact version | `record_human_approval` (no override copy) |
| `task_create/get/list/update_status` | Scoped tracking (`dept="legal"`) | Content task tools |

Existing templates map directly: Legal Review Template (`SOUL.md:62-92`), risk-communication patterns (`:94-99`).

### 3.2 Legal domain lifecycle

`intake → document_ingested (unverified) → first_pass_reviewed → gate_reviewed → approved_for_human_use | rejected`. "Approved" means *approved for a human attorney/owner to act on* — never "approved as legally sufficient." Any document change bumps version and resets review/approval.

### 3.3 Gate = legal gate + human (Legal head) approval

Checks (draft) — all must pass, no override:

- **L1 — No unauthorized-practice claims.** Output contains explicit disclaimer ("first-pass triage, not legal advice; requires licensed attorney review") and no conclusory statements ("this contract is enforceable / compliant"). A disclaimer-free output fails the gate.
- **L2 — Jurisdiction + doc type declared.** Unknown jurisdiction or doc type → `error: missing_context`, never a defaulted guess.
- **L3 — Every risk flag cites clause/section.** Flags without citations fail (analog of F1).
- **L4 — No signature / no filing.** No tool can sign, file, submit, or send anything externally. `record_human_approval` records review readiness only.
- **L5 — PII/secrets redacted before bus persistence of reports.** Reuse `redact.py` BLOCK/FLAG patterns (`:43-60`) on review reports; original client documents stay access-scoped in `central_bus/legal/`.

### 3.4 MVP scope vs deferred

**MVP:** document first-pass review (risk flags + missing standard terms + redline summary vs prior version); license-compatibility checklist (per SOUL `:41, :51-52`); intake summary; L1–L5 gate; human approval; full paper trail (SOUL `:55` — "ถ้าไม่เขียน = ไม่เกิดขึ้น").

**Deferred:** SOC2 / ISO27001 / HIPAA / PCI-DSS certification execution (Compliance Auditor SOUL `:34-40` lists gap assessment + evidence collection — MVP supports evidence *checklists*, never a certification claim); PDPA/GDPR data-governance implementation (SOUL `:42, :52` — flag violations like the session-token example in SOUL `:98`, never remediate code); contract drafting (redline summary only, no generation of binding language); any jurisdiction-specific advice beyond a declared-jurisdiction checklist.

### 3.5 Risks (Legal-specific)

- **Unauthorized practice of law** — the analog of CFO's fabricated numbers. A risk flag read as legal advice is a real-world liability. Mitigation: L1 disclaimer is a gate check, not a suggestion; D3 eval must include adversarial prompts ("is this enforceable?") that must be refused/referred, not answered.
- **False compliance assurance** — "100% license compliant" (SOUL `:113`) must never be emitted by the MCP. Mitigation: license_check returns per-dependency evidence, not a global pass claim.
- **Confidential documents in artifacts** — contracts on bus are sensitive. Mitigation: L5 + scoped bus directory + never in list views (same shape as `task_tracking.py:10-12`).
- **Jurisdiction shopping / wrong law applied** — L2 blocks on unknown jurisdiction.

---

## 4. Sequencing recommendation

### 4.1 Order and dependencies

**Prerequisite (P0) — do not skip:** Content D3 + D4 before cloning the gate pattern to any new pack.

- Content is D1+D2 only; D3 runner exists but has never run (`CERTIFICATION-REGISTRY.md:11`). Cloning an unproven publish gate into money/legal domains propagates an unverified mechanism. P0 exit: D3 eval table (≥20 tasks, expected vs actual + root cause) run by Maker ≠ Checker, then D4 (a different person/agent reproduces from runbook). This also closes the Phase 4 Concat host decision (kickoff §1): ~~decide Concat-disabled-as-suspended vs FUSE workaround first~~ **(settled 2026-11-07: ADR-032 amended → Option 2 EXTRACT สำเร็จ, `concat` enabled, handshake verified; render proof ยังขาด = เหลือ open item เดียว)**, because the Content gate currently special-cases Concat/local render states (`content_service.py:2797-2810`) — the pattern you clone must be the *settled* pattern, not the pre-decision one.
- Docs cleanup (kickoff §2) is a parallel prerequisite for CFO/Legal D1 notes (pack tables must not read as capability claims, §2.1).

**Recommended pack order: Legal first, CFO second — with parallel D1s.**

1. **Parallel D1:** Legal D1 note + CFO D1 note written together (docs only, no code). Both are D0; D1 is the cheapest de-risking step and sequences the builds without blocking each other.
2. **Legal D2 build first (M effort).** Rationale: Legal MVP is read-only triage over client-supplied documents (bus ingestion + checklist + redline diff) with no data-feed dependency and no arithmetic to get wrong. Its D3 is well-defined (≥20 documents, known risk flags, adversarial advice-refusal cases). Its lessons (L-gate implementation, disclaimer enforcement, PII redaction of reports) directly inform CFO's F-gate.
3. **CFO D2 build second (L effort).** Rationale: CFO needs (a) a deterministic recalculation engine that never relies on LLM arithmetic, (b) a tier-enforcement layer, and (c) a numeric D3 ground-truth set — all new work beyond the shell. Building Legal first proves the *new-domain-gate* mechanism on lower-stakes output before applying it to money.

Reversal condition: if CEO judges CFO business value (runway/budget decisions) outweighs Legal's lower automation risk, swap the D2 order — but **do not remove P0**. The P0 (Content D3/D4) is order-independent.

### 4.2 Effort estimates

| Pack | Size | Rationale |
|:-----|:-----|:----------|
| Legal | **M** (~1 head + 1 checker, 4–6 weeks to D3) | Shell reuse (adapter/bus/tasks/gate-shape) is proven; new work = 1 service (`legal_service.py`) + L-gate + redline diff (text diff on stored versions — simple) + disclaimer/jurisdiction guards. No external data feed, no deterministic-calc engine. D3 ground truth is judgmental (risk-flag recall/precision) — needs an attorney-criteria rubric, which is the main cost. |
| CFO | **L** (~1 head + 1 checker, 7–10 weeks to D3) | Shell reuse is proven; new work = 2 services (`cfo_service.py` + deterministic `recalculate` engine) + F-gate + tier enforcement + currency/rounding rules + input reconciliation. D3 ground truth must be *numeric* (≥20 cases, exact totals/variances from known inputs) — harder to build and to judge than Legal's rubric, and a single arithmetic slip is a D3 fail. Data-feed connectors deliberately deferred (§2.4) to keep L from becoming XL. |

S/M/L here = team-weeks to **D3-passed** (not D4), assuming P0 complete and one Maker + one independent Checker. D4 (runbook + reproduction) adds ~1 week per pack.

### 4.3 What must NOT be copied blindly (checklist for any future build PR)

- [ ] Piper/FFmpeg/Concat/Earshot/ElevenLabs, `media_service.py`, 6×15 layout, 1080×1920, 90s default.
- [ ] R1–R5 text heuristics as acceptance criteria. Domain gates (F/L) replace them; R1's *principle* (per-item evidence citation) survives as F1/L3, the heuristics do not.
- [ ] `overrides_failed_checks` approval semantics. CFO/Legal approvals hard-block or escalate by tier — never override.
- [ ] Campaign lifecycle state names where they don't fit (`scaffold` stays in Content; CFO/Legal use §2.2/§3.2).
- [ ] ElevenLabs-style "direct user request = authorized credit use" auto-authorization (`content_mcp.py:73-75`). No CFO/Legal tool may self-authorize spend, filing, or external submission.

---

## 5. PRD alignment

### 5.1 What the MVP PRD already says

- **Scope boundary:** `PRD:117` — Out of Scope: "All departments and all specialist agents." `PRD:103-107` — Must Have includes Content Creator as "the first integrated department module" and "one end-to-end tracked task path" (Content). CFO/Legal are correctly outside MVP.
- **Expansion is anticipated but unsequenced:** `PRD:183` (Phase 5): "More departments and background workers — Prioritize from Beta evidence; certify each department independently." That is the whole sequencing policy: *prioritize from Beta evidence + certify independently.* It names no packs, no order, no per-pack acceptance beyond "certify independently."
- **Architecture hooks exist:** `PRD:41` (department independence), `PRD:45` (module metadata), `PRD:100` (registry records capabilities/permissions), `PRD:155` (department-scoped data directory, no unrelated reads/writes), `PRD:152` (explicit structured status, no failure reported as success). The Local Runtime Design (`SOLOCORP-APP-LOCAL-RUNTIME-DESIGN-v0.1.md:103-114, 136-140`) already reserves `entry_repo` in the registry schema so a split pack needs no app change.
- **Content pilot is historical, not a template mandate:** `PRD:201` — "Existing pilot verification is historical evidence, not certification of the new app." The PRD deliberately does not canonize Content's implementation as the pack template.

### 5.2 Gaps (what the PRD does not cover that CFO/Legal need)

1. No per-pack acceptance criteria beyond "certify independently" (no gate/human-approval requirement for regulated outputs).
2. No regulated-output policy (financial figures, legal conclusions, tax positions) — the PRD's quality language is generic ("explicit structured status," `:151`).
3. No data-provenance requirement for client-supplied inputs (the `client_supplied_unverified` pattern is enforced in Content code, not in the PRD).
4. No approval-tier / authority model (CFO SOUL `:141-148` has one; the PRD has none).
5. No disclaimer / unauthorized-practice guardrail for Legal output.

### 5.3 Proposed PRD update wording (NOT applied — for Architect/CEO approval)

Recommended insertion at §11 Phase 5 and §7 Post-MVP direction. Draft text (English, matching PRD voice):

> **Phase 5 — Product expansion (pack-by-pack).** Each department pack after Content is admitted only when all of the following hold:
>
> 1. **Standalone proof (FR-07).** The pack MCP is usable from at least one external compatible MCP client without the Core MCP or SoloCorp App, with its own department-scoped data directory (PRD §9).
> 2. **Gate + human approval.** The pack defines a domain gate (automated checks with a report artifact stored on the Central Bus) and records human approval for the exact version of the artifact. A gate report is never approval. No pack may auto-approve, auto-publish, auto-file, or move money.
> 3. **Provenance honesty.** Client-supplied inputs are stored and labeled `client_supplied_unverified` until independently reconciled; no tool may present supplied inputs as verified, or generate figures/findings it cannot trace to stored inputs.
> 4. **Independent certification.** The pack passes D1–D4 (rules/06-certification.md) with Maker ≠ Checker at every gate; the registry is updated by the checker/CEO only, with evidence under `bus/evidence/`.
> 5. **Regulated-output packs (CFO, Legal).** Additionally: (a) approval authority is tiered and enforced by tool (amount/jurisdiction tiers), not by convention; (b) failed gate checks block approval — an explicit override of a failed financial or legal check is not a supported operation; (c) Legal output carries a first-pass-triage disclaimer and never states a legal conclusion; CFO output never presents an untraced figure. D3 eval for regulated packs must include adversarial cases (requests to invent figures, state legal conclusions, sign/file/submit) and must refuse them.
>
> Pack order within Phase 5 is prioritized from Beta evidence plus risk: triage/read-only packs (Legal) before money-moving-adjacent packs (CFO), unless Beta evidence shows otherwise. The Content Creator pack is the reference implementation of the governance shell (§§1–4); its domain pipeline (media, R1–R5) is not a template for other packs.

Effect if approved: PRD gains the sequencing logic in §4.1 and the acceptance bar in §6 as product law, instead of relying on individual pack SOULs. No MVP scope change; Phase 5 remains after Beta.

---

## 6. Success criteria per pack (D1–D4)

### 6.1 Shared (both packs)

| Gate | Criterion (evidence-based) |
|:-----|:---------------------------|
| **D1** | 1-page note per pack (5 checks per `rules/06:16`): job, why an agent, which head + tools, permission/scope, done-criteria. Checker (CEO/Owner) signs. No code. |
| **D2** | 50–150-line mini-agent per pack head that really calls tools (bus submit/fetch, task create/status, gate review) with run output + exit code, reproduced by independent verifier (pattern: `CERTIFICATION-REGISTRY.md:11`). |
| **D3** | ≥20-task eval table (expected vs actual + root cause per row, no cherry-picking). Failures included. Tester ≠ Maker. |
| **D4** | Runbook such that a different person/agent reproduces D2/D3 results from a clean checkout. |

### 6.2 CFO-specific

- **D2:** mini-agent ingests a known figure set, recalculates, runs F-gate, records approval — with run log showing F1–F5 checks executed.
- **D3 (≥20 numeric tasks):** budget/variance/runway cases with ground-truth totals; pass = exact totals, zero untraced figures, zero invented figures on missing-input cases; adversarial cases ("estimate the missing revenue") must return `missing_input`, never a number.
- **D4:** second person runs a full budget→gate→approval cycle from runbook and produces identical artifacts (hash-equivalent).

### 6.3 Legal-specific

- **D2:** mini-agent ingests a contract, produces risk flags with clause citations, runs L-gate, records disclaimer-bearing approval — with run log showing L1–L5 executed.
- **D3 (≥20 document tasks):** mixed doc types/jurisdictions with a pre-registered risk-flag rubric; pass = flag recall/precision above the D1 threshold + zero undisclaimed conclusions; adversarial cases ("is this enforceable?", "sign this") must be refused/referred, never answered as advice or executed.
- **D4:** second person reproduces a full intake→review→gate→approval cycle from runbook.

### 6.4 Program exit (pre-Phase 5)

Content D3+D4 complete (P0) → Legal D1 → CFO D1 → Legal D2/D3 → CFO D2/D3 → Legal D4 → CFO D4 → PRD §5.3 wording approved → Phase 5 pack admission per pack, one at a time. No pack is advertised as a capability until its own D4.

---

## Appendix — evidence index

| Claim | File:line |
|:------|:----------|
| Pack line v2.4.0 = CFO/Legal/Content | `README.md:36`, `:255-269` |
| Kickoff scope (decision first, frozen) | `central_bus/content/ceo-phase4-kickoff-20261107_20261107T051623810915Z.md:1-20` |
| Standalone registry seeding | `solocorp_mcp/departments/content_mcp.py:49-62` |
| Registry status without API key | `content_mcp.py:512-526` |
| Head boundary instructions | `content_mcp.py:65-99` |
| Bus data plane contract | `solocorp_mcp/bus_store.py:1-6, 45-51` |
| Department constant + bus I/O | `solocorp_mcp/departments/content_service.py:45, 31-38` |
| Gate → blocked until human approval | `content_service.py:2653-2691`, `:2690` |
| Exact-version approval enforcement | `content_service.py:2773-2879`, `:2790-2796` |
| Approval identity honesty | `content_service.py:2845` |
| Provenance unverified | `content_service.py:2050-2082`, `:2078`; `content_mcp.py:70-71, 347` |
| Lifecycle states | `content_service.py:2887`; scaffold default `:2736-2740` |
| R1–R5 + D0/D1/D2 redaction | `solocorp_skills/redact.py:9-19, 43-60, 221-276` |
| Task envelope + statuses | `solocorp_mcp/task_tracking.py:1-14, 30, 55-80` |
| Scoped task tools | `content_mcp.py:529-620` |
| Registry config/state split | `solocorp_mcp/module_registry.py:3-35` |
| Thinner shell generalization | `solocorp_mcp/departments/engineering_mcp.py:1-22`, `qa_mcp.py:1-41` |
| D-cert ladder | `rules/06-certification.md:14-19, 23-25, 30-36` |
| Registry status (Content D1+D2, others D0) | `profiles/CERTIFICATION-REGISTRY.md:11-13, 28` |
| PRD expansion policy | `docs/prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md:117, 183, 201` |
| PRD standalone + independence | `PRD:41, 73-79, 145` |
| CFO templates/tiers/boundaries | `profiles/02-cfo/SOUL.md:131-148, 154-218, 224-228, 263-281` |
| Legal triage boundary + template | `profiles/13-legal/SOUL.md:41-58, 62-99, 111-118`; `tulya/team/02-legal-document-review.SOUL.md:17-24, 42-44` |
| No CFO/Legal MCP yet | `solocorp_mcp/departments/*.py` (directory listing, 2026-11-07) |

---

*Plan only. No code, no MCP changes, no renders, no PRD edits, frozen campaigns untouched. Next action belongs to CEO/Architect: (1) confirm P0 (Content D3/D4) + Concat decision ordering, (2) approve/adjust §5.3 PRD wording, (3) authorize Legal + CFO D1 notes.*

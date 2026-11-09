# Content Creator MCP — Strategy Reference v1.0

| Field | Value |
|:--|:--|
| Status | Owner-approved direction — reference for team |
| Date | 2026-11-02 |
| Author | Alex (Product Manager consultation) |
| Decided by | Owner (Dr.solodev) — L5 |
| Scope | Content Creator MCP standalone: licensing, release strategy, monetization posture, review cadence |
| Parent doc | [`PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md`](../prds/PRD-SOLOCORP-LOCAL-FIRST-MCP-APP-MVP-v1.0.md) §7 Post-MVP Commercial Direction |

> This document does not replace the MVP PRD. It records the Owner-approved
> strategy for the **Content Creator MCP as a standalone product line** and
> aligns with the PRD's standalone requirement (Phase 3 / FR-07).

---

## 1. Licensing Boundary (Open-Core Split)

### Decision

| Component | License | Rationale |
|:--|:--|:--|
| MCP adapter / protocol contract / tool interface | **Open (MIT)** | Distribution funnel — anyone can connect, try, and adopt; adoption is marketing |
| Content engine, workflows, prompts, premium templates, media pipeline, hosted services | **Closed (proprietary / source-available)** | This is the actual moat — output quality, not the protocol shell |

### Legal status (verified 2026-11-02)

- All code under `axis_mcp/departments/` was authored by **Dr.SoloDev alone**
  (verified via `git log` — no external contributors touched this tree).
  The copyright holder may relicense their own work freely.
- Directory first appeared in git **2026-10-26** (content pilot), current
  architecture **2026-11-02**. The repo is now **private**.
- Old public forks hold only the **pre-architecture, pre-MCP-rewrite version**
  — MIT applies irrevocably to those old snapshots only. They contain no
  MCP department architecture and no product value being protected today.
- **Open check (Owner to confirm):** was any `axis_mcp/departments/`
  commit ever pushed while the repo was still public? If yes, those specific
  snapshots are MIT-pinned (harmless if early/immature). If no — clean.

### Repo split rules (when the split happens)

1. The standalone Content MCP repo starts with its **new license from its
   very first commit** — no MIT header may carry over by accident.
2. Strip MIT references from `LICENSE`, README badges, and package metadata
   in the same initial commit (hygiene, not an afterthought).
3. Keep the **interoperability contract** (how any MCP client connects to the
   module) documented openly — PRD principle: department independence must not
   depend on closed code to *connect*, only to *produce value*.
4. ADR-030 records the accepted open/closed boundary. Before the split, add
   the concrete file-level boundary list so the implementation is reviewable.

### Sequencing

The repo split is **not a side project** — it is the mechanism that proves
**PRD Phase 3 (Standalone Verification)**:

```
Phase 1–2  Build SoloCorp App shell + Content vertical slice (unchanged)
Phase 3    Split Content MCP repo  ← proves standalone + external client (FR-07)
Phase 4    Closed Beta with community
Post-Beta  Monetization decisions (only with evidence)
```

Do not run the split as parallel work. Execute it only after the app's Phase 1–2
gates are stable, as the PRD Phase 3 standalone verification.

---

## 2. Free-First Strategy (Distribution Before Revenue)

### The strategy in one line

> **Base case: free indefinitely.** Grow a community, accumulate users and
> evidence. Monetization is *signal-triggered*, not calendar-triggered.

### Branches

```
BASE CASE     Free forever → the module works as a normal MCP connector.
              Acceptable outcome. Not a failure.

BRANCH A      Growth outpaces expectation (viral content, investor attention,
(positive      partnership offers) → game changes: revisit pricing, funding,
 anomaly)      or a hosted offering. Requires measurable numbers to even see.

BRANCH B      Growth is flat → stay free, keep improving, treat it as an
(accepted)     open connector. Also acceptable — decided in advance so it
              doesn't feel like failure later.
```

### Target market (initial — Owner's own ground)

- **Thai market first** — the Owner's existing Facebook audience: followers
  already waiting for updates and access. Known demand, known channel.
- **Primary jobs-to-be-done:** video production, video scriptwriting,
  story/narrative design.
- **Persona:** Thai content creators / small content teams who publish video
  regularly and want AI assistance for ideation-to-script.
- **Deliberate scope cap:** Thai-only is a *feature* (focus + distribution
  advantage), not a limitation to fix now. English/multi-market = 🔵 Later
  (same engine, no new product).

### Adoption path (initial)

1. Release free to the community, small batches.
2. Owner-made tutorial videos on setup/connection — **external clients first**:
   - OpenCode free tier, or
   - OpenCode GO at $10/month (explicit third-party dependency — acceptable
     for now; PRD Phase 3 requires external-client proof anyway).
3. Meanwhile: keep improving the Content Department + building the SoloCorp Web UI.
4. When the Web UI ships and the department is materially better → revisit
   business model (see review cadence, §4).

### What "free forever" does NOT answer (open L5 question)

The Owner's original premise was *"without a revenue model, how do we survive?"*
Free-forever re-raises it. Candidate answers (Owner decides; none is wrong):

| Option | Pattern |
|:--|:--|
| ① Services from the same community | Paid content-production services / training — tool free, expertise paid (Red Hat pattern) |
| ② Content & audience monetization | The Facebook/YouTube channel itself (sponsorships, courses) funds development |
| ③ Owner-funded | Explicitly a passion/investment project — no external revenue needed |

**PM recommendation:** ① + ② — the community being built *is* the
distribution asset; you can monetize the audience while the tool stays free.

### Explicitly NOT decided (yet)

- Pricing, tiers, paid features — **no evidence exists**; forbidden until
  Beta signals arrive (PRD: pricing work comes after Beta evidence).
- Other department MCPs remain **free and open source** (Owner decision,
  unchanged by this document).

---

## 3. Quality Floor (Gate Before Public Free Release)

**Free ≠ unfinished.** The first community users are a one-shot first
impression; a broken first experience burns people who were *waiting* for it.

### Release gate

The module is cleared for public free release when **all** hold:

- [ ] **The 3-canonical-work test passes:** from a short brief, the module
      produces (a) a video script, (b) a story/narrative outline, (c) a
      content plan — each requiring **≤ 30% manual rework** by the Owner
      before being usable.
- [ ] Failure modes return **explicit structured errors** — never a
      confident wrong answer presented as success.
- [ ] Setup path is documented and reproduced **from a clean machine** by
      following the tutorial script (if the Owner can't follow their own
      video, nobody can).
- [ ] Known limitations are **written down and shown to users** (no hidden
      rough edges — pre-release honesty beats marketing).

### Known rough edges (as of 2026-11-02)

- Owner-tested: "works at a certain level" — multiple parts still need
  refinement (unspecified → must be itemized before gate review).
- Action: Owner converts personal test notes into a **fix list**, then runs
  the gate above. Passing = green light to open the community.

---

## 4. Evidence Tracking + 90-Day Review

### Weekly: 3 numbers (manual count is fine — no telemetry needed)

| # | Metric | Source | Why |
|:--|:--|:--|:--|
| 1 | Community members | Facebook group count | Distribution growth |
| 2 | Successful tasks (approx.) | Users posting results / asking follow-ups | Real usage, not sign-ups |
| 3 | Recurring questions / friction themes | Group posts & DMs | Next-iteration backlog |

Telemetry stays **off by default** (PRD data policy) — manual community
counting is sufficient and respects the privacy stance.

### 90-day review cadence (starts 2026-11-02)

| Checkpoint | Date | Question set |
|:--|:--|:--|
| Review 1 | **2027-02-02** | Growing? Anyone asked to pay? Still want to continue? |
| Review 2 | **2027-05-02** | Same 3 questions + review branch (A/B) |
| Review 3 | **2027-08-02** | Same 3 questions + update or close the strategy |

**Rules:**
- Do not lock a 12–18 month decision today. Decide in 90-day slices.
- If numbers are flat at Review 1 → Branch B confirmed; keep it free without
  re-litigating. Flat is an *answer*, not a failure.
- **Signal that may trigger early monetization review** (don't wait 90 days):
  a user *asks* "how much?" — count these; 3 unsolicited asks = convene early.

---

## 5. Decision Summary (one table)

| # | Decision | Status |
|:--|:--|:--|
| 1 | Content MCP becomes a standalone product line (own repo) | ✅ Approved — execute at PRD Phase 3 |
| 2 | Open-core: adapter open / content engine closed | ✅ Approved — ADR-030 accepted; add file boundary list before split |
| 3 | Old MIT forks: no action needed | ✅ Verified — old snapshots, no product value |
| 4 | Free-first, Thai market, community-led | ✅ Approved |
| 5 | Monetization: signal-triggered, not scheduled | ✅ Approved — no pricing work until evidence |
| 6 | Quality floor gates the public release | ✅ Approved — gate checklist above |
| 7 | Track 3 numbers weekly; 90-day reviews | ✅ Approved — first review 2027-02-02 |
| 8 | Other departments stay free + open source | ✅ Unchanged |

**Trade-off acknowledged:** running a second product line before the SoloCorp
App clears its Phase 1–2 gates is a real focus risk. Mitigation: the split is
bound to Phase 3 (no parallel work), and free release depends on the quality
floor (no half-baked public exposure).

---

*SoloCorp OS — System First, Everything Follows*

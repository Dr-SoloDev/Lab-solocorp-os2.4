# Audit Finding Reassessment Methodology

**Source:** Session 2026-06-18, คุณวุฒิ (Architect) review of Scrap POS audit findings
**Key Insight:** Surface-level severity ≠ actual severity. Every finding must be verified against real code.

---

## The Reassessment Cycle

```
[Audit Finding Received]
         │
         ▼
[Step 1: Locate in Codebase]
  - grep/search for the mentioned function/feature
  - Read the actual implementation, not just the report
         │
         ▼
[Step 2: Verify Implementation]
  - Does it exist? → If not, flag as REMOVED / NOT APPLICABLE
  - Does it WORK? → Test with actual input, inspect output
  - Is it CALLED? → Search for all callers across the codebase
         │
         ▼
[Step 3: Map Real Impact]
  - List every file that depends on this function
  - For each caller: is there a fallback/alternative?
  - Example: escapeHtml() was broken in common.js, but
    sellers.js/sale-lots.js/branches.js had their OWN working
    implementation → dashboard.js was the only real victim
         │
         ▼
[Step 4: Reassess Severity]
  - Original severity (as reported) vs Actual severity
  - Adjust based on real impact scope
  - Document WHY severity changed
         │
         ▼
[Step 5: Estimate Effort + Risk]
  - How long to fix?
  - What's the risk of the fix?
  - Is this a quick win or a major refactor?
         │
         ▼
[Step 6: Build Dependency Chain]
  - Finding A blocks Finding B (e.g., XSS blocks httpOnly cookie)
  - Independent findings can be done in parallel
  - Priority = risk reduction ÷ effort, adjusted for dependencies
```

---

## Real Examples

### Example 1: escapeHtml() — Severity INCREASED

```
Original finding: "escapeHtml() หายในบาง view"  [CRITICAL]

Verification:
  ↓ Found function in common.js:133
  ↓ Inspected implementation → template render bug, completely BROKEN
  ↓ Traced ALL callers → dashboard.js ONLY (other files had their own)
  
Reassessment: CRITICAL → HIGH (impact narrowed to dashboard)
But: dashboard = admin home page, first thing staff sees
Actually: HIGH (Stored XSS on main admin page)

Recommendation: Fix in 15 minutes — quick win
```

### Example 2: ID Card Photo Encryption — REMOVED

```
Original finding: "ID card photos ไม่ได้ encrypt" [HIGH]

Verification:
  ↓ Searched for id_card_img across entire codebase
  ↓ Searched sellers table schema
  ↓ No id_card_img column exists
  ↓ No upload endpoint for ID card photos
  ↓ Feature does NOT exist yet

Reassessment: HIGH → NOT APPLICABLE (feature not implemented)
Recommendation: Remove from audit, or reclassify as "architectural concern for future"
```

### Example 3: JWT localStorage — Severity CONFIRMED but Dependent

```
Original finding: "JWT เก็บใน localStorage" [HIGH]

Verification:
  ↓ Found in login.js:37-38 → localStorage.setItem('posToken', ...)
  ↓ Found in common.js:3-7 → localStorage.getItem('posToken')
  ↓ Found in common.js:95-98 → Bearer token in Authorization header
  
Reassessment: HIGH (confirmed) — but blocks on XSS fix first
Chain: XSS (F1) → steal localStorage token → account takeover
Fix order: 1. Fix XSS first, 2. THEN migrate to httpOnly cookie
```

---

## When to SKIP (leave as "defer")

Some findings are real but low risk or expensive to fix now:

| Signal | Example | Action |
|--------|---------|--------|
| Fix risks breaking production | Docker root → Apache port binding | Defer with documented approach |
| Fix requires architectural change | JWT → httpOnly cookie needs CSRF too | Schedule for dedicated sprint |
| Cosmetic/Low severity | Logout doesn't call API | Defer until touched by other work |
| No exploit chain currently known | Docker root (would need initial breach) | Defer |

---

## Output Format

```markdown
| # | Finding | Original | Actual | Status |
|---|---------|----------|--------|--------|
| F1 | escapeHtml | CRITICAL | HIGH ↓ | Fix in 15m |
| F2 | JWT in localStorage | HIGH | HIGH → | Blocked by F1 |
| F3 | DB password weak | HIGH | HIGH → | Independent |
| F4 | ID card photos | HIGH | REMOVED ✗ | Feature absent |
| F5 | Docker root | HIGH | MEDIUM ↓ | Defer |
| F6 | Logout token | LOW | LOW → | Defer |
```

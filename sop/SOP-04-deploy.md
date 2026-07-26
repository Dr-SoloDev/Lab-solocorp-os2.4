# SOP-04: Deploy - Profiles, Skills, Config

**Owner:** Engineering (chang fool)
**Version:** v2.0
**Applies to:** Engineering, QA, CEO

---

## QA Sign-off Gate (MANDATORY)

> **No QA sign-off = No deploy**

Before every deploy, a QA sign-off gate record is required:
- Feature name, tester name, date
- Test results evidence path
- Minimum thresholds (see below)

---

## Step-by-Step

### 1. Pre-deploy Checks
- [ ] Pull latest: `git pull`
- [ ] Run tests: `pytest tests/ central_bus/tests/ -q`
- [ ] If tests fail -> **no deploy** -> fix first

### 2. QA Sign-off Gate

> **Mandatory step - do not skip**

```bash
python3 workers/qa_signoff_gate.py \
  --feature "<feature-name>" \
  --status APPROVED \
  --tester "<tester-name>" \
  --coverage 80 \
  --regression-pass
```

Or using a test results file:

```bash
python3 workers/qa_signoff_gate.py \
  --feature "<feature-name>" \
  --test-results "test-output.json" \
  --tester "<tester-name>"
```

#### Checklist before sign-off
- [ ] Test coverage >= 80%
- [ ] Critical bugs = 0
- [ ] High bugs = 0
- [ ] All regression tests pass
- [ ] All API endpoint tests complete
- [ ] Edge cases tested
- [ ] Test evidence recorded
- [ ] If failed tests exist -> documented known issues

#### Gate Blocks (auto REJECTED)
| Condition | Threshold |
|:-----------|:----------|
| Test coverage | < 70% |
| Critical bugs | > 0 |
| High bugs | > 0 |
| Regression pass | = false |

#### Conditional (requires documented conditions)
| Condition | Threshold |
|:-----------|:----------|
| Test coverage | >= 70% but < 80% |
| Medium bugs | > 3 |
| Low bugs | > 10 |

#### No deploy if
- No QA sign-off record -> REJECT
- QA sign-off status = REJECTED -> REJECT
- QA sign-off status = CONDITIONAL and conditions not resolved -> REJECT

---

### 3. Build
```bash
python3 scripts/build-profiles.py
python3 scripts/export-codex-agents.py
```

### 4. Validate
```bash
python3 scripts/export-codex-agents.py --validate-only
python3 scripts/validate-soul-profiles.py
```

### 5. QA Smoke Test (if QA involved)
- Run smoke test scripts
- Verify feature works in real environment

### 6. Commit
```bash
git add <relevant files>
git commit -m "deploy: <summary>"
git push
```

### 7. Report
- Summary of deployed items (3-5 bullets)
- Evidence: pass/fail
- Include QA sign-off record link
- Send to CEO (L2) - Owner doesn't need to know

---

## Rollback
If deploy has issues:
```bash
git revert HEAD
git push
```
Notify CEO and relevant departments immediately.

---

## Minimum Threshold Reference

| Metric | APPROVED | CONDITIONAL | REJECTED |
|:--------|:---------|:------------|:---------|
| Test Coverage | >= 80% | >= 70% | < 70% |
| Critical Bugs | = 0 | = 0 | > 0 |
| High Bugs | = 0 | = 0 | > 0 |
| Medium Bugs | <= 3 | > 3 | - |
| Low Bugs | <= 10 | > 10 | - |
| Regression Pass | PASS | PASS | FAIL |

> Note: CONDITIONAL requires documented conditions + timeline for resolution

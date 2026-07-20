# SOP-04: Deploy — Profiles, Skills, Config

**Owner:** Engineering (ช่างฟูล)  
**Version:** v2.0  
**Applies to:** Engineering, QA, CEO

---

## QA Sign-off Gate (MANDATORY)

> **ไม่มี QA sign-off = ห้าม deploy**

ก่อน deploy ทุกครั้ง ต้องมี QA sign-off gate record ก่อน:
- Feature name, tester name, date
- Test results evidence path
- Minimum thresholds (see below)

---

## Step-by-Step

### 1. Pre-deploy Checks
- [ ] ดึง latest: `git pull`
- [ ] รัน tests: `pytest tests/ central_bus/tests/ -q`
- [ ] ถ้า tests fail → **ห้าม deploy** → fix ก่อน

### 2. QA Sign-off Gate ⚠️

> **ขั้นตอนบังคับ — ห้ามข้ามเด็ดขาด**

```bash
python3 workers/qa-signoff-gate.py \
  --feature "<feature-name>" \
  --status APPROVED \
  --tester "<tester-name>" \
  --coverage 80 \
  --regression-pass
```

หรือใช้ test results file:

```bash
python3 workers/qa-signoff-gate.py \
  --feature "<feature-name>" \
  --test-results "test-output.json" \
  --tester "<tester-name>"
```

#### ✅ Checklist ก่อน sign-off
- [ ] Test coverage ≥ 80%
- [ ] Critical bugs = 0
- [ ] High bugs = 0
- [ ] Regression tests ผ่านทั้งหมด
- [ ] API endpoint tests ครบทุก endpoint
- [ ] Edge cases ได้รับการทดสอบ
- [ ] Test evidence บันทึกเรียบร้อย
- [ ] ถ้ามี failed tests → documented known issues

#### ❌ Gate Blocks (ทำให้ REJECTED โดยอัตโนมัติ)
| Condition | Threshold |
|:-----------|:----------|
| Test coverage | < 70% |
| Critical bugs | > 0 |
| High bugs | > 0 |
| Regression pass | = false |

#### ⚠️ Conditional (ต้องมี documented conditions)
| Condition | Threshold |
|:-----------|:----------|
| Test coverage | ≥ 70% แต่ < 80% |
| Medium bugs | > 3 |
| Low bugs | > 10 |

#### 🚫 ห้าม deploy ถ้า
- ❌ ไม่มี QA sign-off record → **REJECT**
- ❌ QA sign-off status = REJECTED → **REJECT**
- ❌ QA sign-off status = CONDITIONAL และยังไม่ resolved conditions → **REJECT**

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

### 5. QA Smoke Test (ถ้ามี QA involvement)
- รัน smoke test scripts
- Verify ว่า feature ทำงานใน environment จริง

### 6. Commit
```bash
git add <relevant files>
git commit -m "deploy: <summary>"
git push
```

### 7. รายงาน
- สรุปสิ่งที่ deploy (3-5 bullet)
- Evidence: ผ่าน/ไม่ผ่าน
- แนบลิงก์ QA sign-off record
- ถึง CEO (L2) — Owner ไม่ต้องรู้

---

## Rollback
ถ้า deploy มีปัญหา:
```bash
git revert HEAD
git push
```
แจ้ง CEO + department ที่เกี่ยวข้องทันที

---

## Minimum Threshold Reference

| Metric | APPROVED | CONDITIONAL | REJECTED |
|:--------|:---------|:------------|:---------|
| Test Coverage | ≥ 80% | ≥ 70% | < 70% |
| Critical Bugs | = 0 | = 0 | > 0 |
| High Bugs | = 0 | = 0 | > 0 |
| Medium Bugs | ≤ 3 | > 3 | — |
| Low Bugs | ≤ 10 | > 10 | — |
| Regression Pass | ✅ | ✅ | ❌ |

> Note: CONDITIONAL requires documented conditions + timeline for resolution

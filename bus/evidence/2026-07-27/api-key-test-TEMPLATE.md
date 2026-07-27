# API Key Protection — Test Report Template

**Tester:** [Your Name / Department]
**Date:** 2026-07-27
**Branch:** main
**Commit Hash:** [run: git rev-parse --short HEAD]

---

## Test Results

| Test Case | Expected | Result | Notes |
|-----------|----------|--------|-------|
| 1. Normal file commit | ✅ Pass | ⬜ ✅ / ❌ | Should allow commit |
| 2. File with API key | ❌ Block | ⬜ ✅ / ❌ | Should block commit |
| 3. Force add .env | ❌ Block | ⬜ ✅ / ❌ | Should block even with -f |
| 4. Cleanup | ✅ Clean | ⬜ ✅ / ❌ | Working directory clean |

---

## Detailed Test Output

### Test 1: Normal File
```bash
# Command:
echo "print('Hello')" > test_normal.py
git add test_normal.py
git commit -m "Test normal"

# Output:
[paste output here]
```

**Result:** ⬜ PASS / ⬜ FAIL

---

### Test 2: File with API Key
```bash
# Command:
echo "KEY='ccsk-1234...'" > test_secret.py
git add test_secret.py
git commit -m "Test secret"

# Output:
[paste output here]
```

**Result:** ⬜ BLOCKED / ⬜ NOT BLOCKED (bug!)

---

### Test 3: Force Add .env
```bash
# Command:
git add -f .env
git commit -m "Test env"

# Output:
[paste output here]
```

**Result:** ⬜ BLOCKED / ⬜ NOT BLOCKED (bug!)

---

## Issues Found

**None** ⬜ OR:

1. [Issue description]
   - Severity: ⬜ Critical / ⬜ High / ⬜ Medium / ⬜ Low
   - Steps to reproduce:
   - Expected behavior:
   - Actual behavior:

---

## Environment

- OS: [Linux / macOS / Windows]
- Git version: [run: git --version]
- Shell: [bash / zsh / other]
- Hook installed: [run: ls -la .git/hooks/pre-commit]

---

## Overall Assessment

⬜ **PASS** — All tests passed, ready for production
⬜ **PASS with notes** — Minor issues but safe to use
⬜ **FAIL** — Critical issues found, need fixes

---

## Sign-off

**Tested by:** [Your Name]
**Department:** [Your Department]
**Date:** 2026-07-27
**Signature:** [Your GitHub username]

---

**Submit this report to:** `bus/evidence/2026-07-27/api-key-test-[yourname].md`

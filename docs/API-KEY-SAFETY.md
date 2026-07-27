## 🛡️ API Key Safety — Quick Reference

### ✅ DO
```bash
# Store in .env
MAXPLUS_API_KEY=ccsk-xxx

# Load in code
import os
API_KEY = os.getenv("MAXPLUS_API_KEY")
```

### ❌ DON'T
```python
# Hardcode
API_KEY = "ccsk-xxx"  # ❌ NEVER!
```

### 🚨 If Leaked
1. Revoke key immediately
2. Generate new key
3. Update .env
4. Never commit .env

### 🔍 Protection Layers
1. `.gitignore` — blocks .env files
2. Pre-commit hook — scans for secrets
3. Code review — human verification

**Full guide:** `docs/API-KEY-PROTECTION.md`

# 🛡️ API Key Protection Guide

> SoloCorp OS — ป้องกัน API Key Leak ไปบน GitHub

## Overview

ระบบป้องกัน 3 ชั้น:
1. **`.gitignore`** — ป้องกันไม่ให้ track `.env` files
2. **Pre-commit Hook** — สแกนหา secrets ก่อน commit
3. **Code Review** — human verification (L3+)

---

## 🔒 Layer 1: `.gitignore`

ไฟล์ที่ถูก ignore:

```gitignore
.env
.env.local
.env.production
*.key
*.pem
secrets.json
```

✅ **อยู่ใน `.gitignore` แล้ว** — ไม่ต้องทำอะไร

---

## 🚨 Layer 2: Pre-commit Hook

### อยู่ที่ไหน
```
.git/hooks/pre-commit
```

### Pattern ที่ตรวจสอบ

| Pattern | Example |
|---------|---------|
| `ccsk-[a-f0-9]{64}` | Maxplus AI API Key |
| `sk-[A-Za-z0-9]{48,}` | OpenAI API Key |
| `MAXPLUS_API_KEY=ccsk-` | Hardcoded Maxplus |
| `OPENAI_API_KEY=sk-` | Hardcoded OpenAI |
| `AWS_SECRET_ACCESS_KEY=` | AWS Secret |
| `GITHUB_TOKEN=` | GitHub Token |
| `password\s*=\s*['\"][^'\"]{8,}` | Password in code |

### การทำงาน

```bash
# ✅ ไฟล์ปกติ — commit ผ่าน
git add normal_file.py
git commit -m "Update code"
# 🔍 Checking for API keys and secrets...
# ✅ No secrets detected

# ❌ ไฟล์มี API Key — commit ถูก block
git add file_with_key.py
git commit -m "Add feature"
# 🔍 Checking for API keys and secrets...
# ❌ BLOCKED: Found potential API key in file_with_key.py
# 🚨 COMMIT BLOCKED: API Key หรือ Secret ถูกตรวจพบ!
```

### Bypass Hook (ระวัง!)

```bash
# ถ้าแน่ใจว่าไม่ใช่ secret จริง (เช่น test data)
git commit --no-verify
```

⚠️ **ใช้ `--no-verify` เฉพาะเมื่อแน่ใจ 100%!**

---

## 📋 Layer 3: Code Review Checklist

สำหรับ L3+ decisions:

- [ ] ไม่มี hardcoded API keys
- [ ] ไม่มี credentials ใน code
- [ ] ใช้ `os.getenv()` สำหรับ sensitive data
- [ ] `.env` ถูก ignore แล้ว
- [ ] `.env.example` ใช้ placeholder เท่านั้น

---

## 🔧 How to Use API Keys Safely

### ✅ Correct Way

**1. Store in `.env`:**
```bash
MAXPLUS_API_KEY=ccsk-8fc78b9689f73b15419b6236663b8b6246a8deec299517b01f4b5c05a890ef57
```

**2. Load in code:**
```python
import os

API_KEY = os.getenv("MAXPLUS_API_KEY", "")
if not API_KEY:
    raise ValueError("MAXPLUS_API_KEY not found in environment")
```

**3. Use `.env.example` as template:**
```bash
MAXPLUS_API_KEY=your-api-key-here
```

### ❌ Wrong Way

```python
# ❌ Hardcoded API key
API_KEY = "ccsk-8fc78b9689f73b15419b6236663b8b6246a8deec299517b01f4b5c05a890ef57"

# ❌ Commented API key (still dangerous!)
# API_KEY = "ccsk-8fc78b9689f73b15419b6236663b8b6246a8deec299517b01f4b5c05a890ef57"

# ❌ Config file tracked by git
config.json:
{
  "api_key": "ccsk-8fc78b9689f73b15419b6236663b8b6246a8deec299517b01f4b5c05a890ef57"
}
```

---

## 🚨 What If API Key Leaked?

### Immediate Actions

1. **Revoke the key immediately** — ที่ provider dashboard
2. **Generate new key** — และอัพเดท `.env`
3. **Force push history rewrite** — ลบ key ออกจาก git history:

```bash
# ⚠️ Dangerous — ต้องทำใน safe environment
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

git push origin --force --all
```

4. **Notify team** — ให้ทุกคน pull ใหม่
5. **Monitor usage** — ดูว่ามี unauthorized usage ไหม

---

## 📊 Testing Protection

### Test Pre-commit Hook

```bash
# Test 1: ไฟล์ปกติ (ควรผ่าน)
echo "print('hello')" > test.py
git add test.py
git commit -m "Test normal file"
# ✅ Should pass

# Test 2: ไฟล์มี API key (ควรถูก block)
echo "API_KEY='ccsk-1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'" > test.py
git add test.py
git commit -m "Test with key"
# ❌ Should be blocked

# Cleanup
rm test.py
git reset HEAD test.py
```

### Test .gitignore

```bash
# .env ไม่ควรปรากฏใน status
git status
# ไม่มี .env ใน list

# แม้ force add ก็ควรถูก hook block
git add -f .env
git commit -m "Try to commit .env"
# ❌ Should be blocked by pre-commit hook
```

---

## 🔍 Audit Checklist

### สำหรับ Team Lead / Security Officer

- [ ] ตรวจสอบ `.gitignore` มี `.env` patterns
- [ ] Pre-commit hook ติดตั้งและใช้งานได้
- [ ] `.env.example` ไม่มี real API keys
- [ ] Code ทั้งหมดใช้ `os.getenv()` ไม่ hardcode
- [ ] Documentation อัพเดทให้ทีมรู้
- [ ] ทุกคนใน team รู้วิธี rotate keys เมื่อจำเป็น

---

## 📚 References

- `.gitignore` — Line 6, 102
- `.git/hooks/pre-commit` — Active hook script
- `.env.example` — Safe template
- `workers/maxplus_llm_provider.py` — Example of safe env usage

---

## 🆘 Support

หากพบ API key leak หรือมีคำถาม:

1. **Immediate:** Contact @ceo-turbo หรือ @security
2. **Non-urgent:** สร้าง issue ใน repo (ไม่ใส่ key จริง!)
3. **Documentation:** อัพเดท doc นี้ตามสถานการณ์จริง

---

**Last Updated:** 2026-07-27
**Owner:** CEO (เทอโบ) + CyberSec Team
**Status:** ✅ Active Protection

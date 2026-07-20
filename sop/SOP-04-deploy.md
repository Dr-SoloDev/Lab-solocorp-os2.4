# SOP-04: Deploy — Profiles, Skills, Config

**Owner:** Engineering (ช่างฟูล)  
**Version:** v1.0  
**Applies to:** Engineering, QA, CEO

## Step-by-Step

### 1. Pre-deploy Checks
- [ ] ดึง latest: `git pull`
- [ ] รัน tests: `pytest tests/ central_bus/tests/ -q`
- [ ] ถ้า tests fail → **ห้าม deploy** → fix ก่อน

### 2. Build
```bash
python3 scripts/build-profiles.py
python3 scripts/export-codex-agents.py
```

### 3. Validate
```bash
python3 scripts/export-codex-agents.py --validate-only
python3 scripts/validate-soul-profiles.py
```

### 4. QA Smoke Test
ถ้ามี QA involvement → รัน smoke test scripts

### 5. Commit
```bash
git add <relevant files>
git commit -m "deploy: <summary>"
git push
```

### 6. รายงาน
- สรุปสิ่งที่ deploy (3-5 bullet)
- Evidence: ผ่าน/ไม่ผ่าน
- ถึง CEO (L2) — Owner ไม่ต้องรู้

## Rollback
ถ้า deploy มีปัญหา:
```bash
git revert HEAD
git push
```
แจ้ง CEO + department ที่เกี่ยวข้องทันที

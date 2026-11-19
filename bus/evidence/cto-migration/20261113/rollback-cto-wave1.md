# Rollback — CTO Wave1 dual-run (≤15 นาที)

> Orchestrator (พี่วุฒิ) | trace: ดู `w1-manifest.json`

## เงื่อนไข rollback
- `cto` host unhealthy / `engineering` หรือ `qa` หายจาก config / dual-run ผิดทาง / Owner/CEO สั่งถอย

## ขั้นตอน (≤15 นาที)
1. **Restore config (1 นาที)**
   ```bash
   DATE=20261113
   cp bus/evidence/cto-migration/$DATE/opencode.json.bak opencode.json
   python3 -c "import json; d=json.load(open('opencode.json')); print(sorted(d['mcp']['servers']))"
   # ต้องเหลือ 8 servers เดิม ไม่มี cto, ไม่มี skills/@axis/cto
   ```
2. **Restart MCP (2 นาที)**
   ```bash
   scripts/restart-mcp.sh --yes
   ```
3. **Verify (3 นาที)**
   ```bash
   python3 -c "import json; s=json.load(open('opencode.json'))['mcp']['servers']; assert 'cto' not in s and 'engineering' in s and 'qa' in s; print('rollback ok: cto gone, eng/qa kept')"
   ```
4. **ถอน artifacts Wave1 (ถ้าต้องถอยหมด, 5 นาที)** — ลบเฉพาะไฟล์ Orchestrator (ห้ามแตะ Legal DRAFT + sibling `axis_mcp/cto/**`):
   ```bash
   rm -rf skills/@axis/cto profiles/cto/cto.md profiles/cto/routing.yaml axis_mcp/departments/cto_mcp.py
   # profiles/INDEX.md: ตัด section "## CTO — C-Level" ท้ายไฟล์ออก (append-only revert)
   # bus/evidence/cto-migration/20261113/ เก็บไว้เป็น audit (ห้ามลบ)
   ```
5. **Re-verify + รายงาน CEO (4 นาที)**: pytest scoped หรือ `/status`, แจ้ง CEO ว่าถอยแล้ว

## หมายเหตุ
- `bus/evidence/**` ห้ามลบ (audit trail, SOP-06)
- Legal DRAFT (`CTO.SOUL.md`, `ROUTING_MATRIX.md`) ไม่ใช่ของ Wave1 — ห้ามลบ khi rollback
- Sibling `axis_mcp/cto/**` + DB เป็นงานอีก wave — ประสานก่อนแตะ

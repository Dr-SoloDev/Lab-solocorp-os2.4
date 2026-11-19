# Rollback — CTO Wave2 flip-default (≤15 นาที)

> Orchestrator (พี่วุฒิ) | trace: `cto-mig-W2-20261112T224226Z`

## เงื่อนไข rollback
- `opencode.json` invalid / `cto` หาย / `engineering`+`qa` หาย / E2E `@cto` แดง / Owner/CEO สั่งถอย

## ขั้นตอน (≤15 นาที)
1. **Restore config (1 นาที)**
   ```bash
   DATE=20261113
   cp bus/evidence/cto-migration/$DATE/w2-opencode-pre-flip.bak opencode.json
   python3 -c "import json; d=json.load(open('opencode.json')); print(sorted(d['mcp']['servers'])); print(d['command']['pipeline']['template'][:80])"
   # ต้องกลับเป็น pre-W2: pipeline ใช้ @architect-songsak, eng-deploy @axis/engineering/deploy, smoke-test @axis/qa/smoke-test
   ```
2. **Restore rules + MCP metadata (3 นาที)**
   ```bash
   git diff --stat  # ต้องเห็นแค่ 4 ไฟล์ Wave2
   git checkout HEAD -- rules/01-receive.md axis_mcp/departments/engineering_mcp.py axis_mcp/departments/qa_mcp.py
   # หรือถ้า commit แล้ว: git revert <w2-commit> (1 commit แยก, ห้าม squash)
   ```
3. **Restart MCP (2 นาที)**
   ```bash
   scripts/restart-mcp.sh --yes
   ```
4. **Verify (3 นาที)**
   ```bash
   source .venv/bin/activate
   python3 -c "from axis_mcp.departments import engineering_mcp, qa_mcp; import json; print(json.loads(engineering_mcp.engineering_department_info())['department'])"
   python -m pytest tests/test_qa_mcp.py -q
   ```
5. **รายงาน CEO (2 นาที)**: แจ้งว่าถอย Wave2 แล้ว, queue 0/0/0, dispatch 27 historical คงเดิม

## หมายเหตุ
- `bus/evidence/**` ห้ามลบ (audit trail, SOP-06)
- `central_bus/content/qa_results/qa-w2-e2e-cto-*.json` เป็น evidence จริง — เก็บไว้ ไม่ต้องลบ khi rollback
- Sibling WIP (`w2-health.json` trace `cto-wave2-20261113`, `w2-architect-*` commit 9eabdd4) ไม่ใช่ของ Wave2 นี้ — ห้ามแตะ khi rollback
- Pre-flip backup: `bus/evidence/cto-migration/20261113/w2-opencode-pre-flip.bak` sha `1fa373ec88cf34a0960285f65ef986545045629c19f6f6ae6adc803c9015e583`
- Post-flip sha: `eb260853db55ba66505247030432662e6c90a8de7bc74cb8d915699ca7f13506`

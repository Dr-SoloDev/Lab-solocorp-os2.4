#!/usr/bin/env bash
# ==============================================================================
# CEO Session Start — Auto-Load Protocol
#
# รันทุกครั้งที่ CEO เริ่ม session ใหม่ (ข้าม platform)
# อ่าน brain -> query Central Bus -> รายงานสรุป
#
# วิธีใช้:
#   bash scripts/ceo-session-start.sh
# ==============================================================================

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

if [[ -d .venv ]]; then
    PYTHON=".venv/bin/python3"
else
    PYTHON="python3"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     👑 CEO Session Start — Auto-Load Protocol               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── 1. CEO Identity ──────────────────────────────────────────────────
echo "📖 [1/6] CEO Identity..."
if [[ -f brain/ceo-identity.md ]]; then
    IDENTITY=$(head -5 brain/ceo-identity.md)
    echo "  ✅ CEO รู้จักตัวเอง: ${IDENTITY%%$'\n'*}"
fi

# ── 2. CEO Memory ────────────────────────────────────────────────────
echo "📖 [2/6] CEO Memory..."
if [[ -f brain/ceo-memory.json ]]; then
    $PYTHON -c "
import json
with open('brain/ceo-memory.json') as f:
    mem = json.load(f)
org = mem.get('organization', {})
print(f'  ✅ รู้จัก {org.get(\"total_departments\", \"?\")} departments')
print(f'  ✅ สถานะ: {org.get(\"status\", \"?\")}')
if mem.get('sessions'):
    print(f'  ✅ Session logs: {len(mem[\"sessions\"])} sessions')
if mem.get('lessons_learned'):
    print(f'  ✅ Lessons learned: {len(mem[\"lessons_learned\"])} lessons')
"
fi

# ── 3. Session Log ────────────────────────────────────────────────────
echo "📖 [3/6] Session History..."
if [[ -f brain/session-log.md ]]; then
    LINES=$(wc -l < brain/session-log.md)
    LAST=$(tail -3 brain/session-log.md 2>/dev/null | head -1)
    echo "  ✅ ${LINES} lines of session history"
    echo "  📝 Last entry: ${LAST:0:60}..."
fi

# ── 4. Learnt ─────────────────────────────────────────────────────────
echo "📖 [4/6] Lessons Learned..."
if [[ -f brain/learnt.md ]]; then
    LESSONS=$(grep -c '^- \[' brain/learnt.md 2>/dev/null || echo "0")
    echo "  ✅ ${LESSONS} lessons documented"
fi

# ── 5. Central Bus ────────────────────────────────────────────────────
echo "📡 [5/6] Central Bus Status..."
if curl -s http://127.0.0.1:8099/v1/health >/dev/null 2>&1; then
    $PYTHON -c "
import json, urllib.request
H = {'Content-Type': 'application/json', 'X-API-Key': 'sk-solocorp-admin-local-dev-001'}
try:
    r = urllib.request.urlopen('http://127.0.0.1:8099/v1/health', timeout=3)
    d = json.loads(r.read())
    print(f'  ✅ Central Bus running — uptime: {d.get(\"uptime\", \"?\")}s')
    print(f'  ✅ Facts count: {d.get(\"facts_count\", 0)}')
except Exception as e:
    print(f'  ⚠️ {e}')
"
else:
    echo "  ⚠️ Central Bus not running — start with: bash scripts/bootstrap-ceo.sh --bus-only"

# ── 6. Summary ────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  👑 CEO พร้อมทำงานครับ Owner!                                ║"
echo "║                                                              ║"
echo "║  What's next?                                                ║"
echo "║  ┌─ /status      — ดูสถานะภาพรวม                             ║"
echo "║  ├─ /deploy      — Deploy profiles + agents                  ║"
echo "║  ├─ /brain <msg> — บันทึก session ลง memory                  ║"
echo "║  └─ หรือแค่พิมพ์ภารกิจที่ต้องการ — ผมจัดการให้               ║"
echo "╚══════════════════════════════════════════════════════════════╝"

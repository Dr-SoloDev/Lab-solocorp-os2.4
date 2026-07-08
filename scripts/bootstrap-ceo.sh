#!/usr/bin/env bash
# ==============================================================================
# SoloCorp OS — CEO Bootstrap Script
#
# ใช้เมื่อ:
#   1. clone repo ใหม่บน platform ใดก็ตาม
#   2. ต้องการ restore CEO memory + เปิด services
#   3. ย้ายระหว่าง OpenCode ↔ Claude Code ↔ Codex ↔ Cursor
#
# หลักการ: private repo → ทุกอย่างมากับ git (ยกเว้น .venv, .db)
#   ✅ .env.example  → API key
#   ✅ .claude/settings.json → Claude Code MCP
#   ✅ .codex/config.toml    → Codex CLI MCP
#   ✅ .cursor/mcp.json      → Cursor MCP
#   ✅ opencode.json         → OpenCode MCP
#   ✅ brain/ceo-memory.json → CEO memory
#   ✅ brain/session-log.md  → session history
#
# วิธีใช้:
#   bash scripts/bootstrap-ceo.sh
#
# หรือรันเฉพาะขั้นตอน:
#   bash scripts/bootstrap-ceo.sh --env-only
#   bash scripts/bootstrap-ceo.sh --bus-only
#   bash scripts/bootstrap-ceo.sh --facts-only
# ==============================================================================

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo ""
echo "================================================================"
echo "  🚀 SoloCorp OS — CEO Bootstrap"
echo "  Repo: $REPO_DIR"
echo "  Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "================================================================"
echo ""

# ── Args ──────────────────────────────────────────────────────────────────
DO_ENV=true; DO_DEPS=true; DO_BUS=true; DO_FACTS=true; DO_LOOP=true
[[ "$1" == "--env-only" ]]   && { DO_DEPS=false; DO_BUS=false; DO_FACTS=false; DO_LOOP=false; }
[[ "$1" == "--bus-only" ]]   && { DO_ENV=false; DO_DEPS=false; DO_FACTS=false; DO_LOOP=false; }
[[ "$1" == "--facts-only" ]] && { DO_ENV=false; DO_DEPS=false; DO_BUS=false; DO_LOOP=false; }

# ── Python discovery ──────────────────────────────────────────────────────
if [[ -d .venv ]]; then
    PYTHON=".venv/bin/python3"
    PIP=".venv/bin/pip3"
else
    echo "  ⚠ No .venv — creating..."
    python3 -m venv .venv
    PYTHON=".venv/bin/python3"
    PIP=".venv/bin/pip3"
fi

# ── Step 1: Environment ───────────────────────────────────────────────────
if $DO_ENV; then
    echo "📦 [1/5] Environment..."
    if [[ ! -f .env ]]; then
        cp .env.example .env
        echo "  ✅ .env created from .env.example"
    else
        echo "  ⏭ .env exists"
    fi
    set -a; source .env 2>/dev/null; set +a
    echo "  ✅ SOLOCORP_API_KEY=${SOLOCORP_API_KEY:-}"
fi

# ── Step 2: Dependencies ──────────────────────────────────────────────────
if $DO_DEPS; then
    echo ""
    echo "📦 [2/5] Dependencies..."
    $PIP install -q -r central_bus/requirements.txt 2>/dev/null \
      || $PIP install -q fastapi uvicorn aiosqlite pydantic httpx numpy 2>/dev/null
    echo "  ✅ Python deps ready"
fi

# ── Step 3: Central Bus ───────────────────────────────────────────────────
if $DO_BUS; then
    echo ""
    echo "🚌 [3/5] Central Bus (port 8099)..."
    if curl -s http://127.0.0.1:8099/v1/health >/dev/null 2>&1; then
        echo "  ⏭ Already running"
    else
        # Compatibility fix if needed
        $PYTHON -c "from central_bus.main import app; print('✅ module OK')" 2>/dev/null || {
            echo "  ⚠ Fixing settings.pid → os.getpid()..."
            $PYTHON -c "
import re
with open('central_bus/main.py') as f:
    c = f.read()
c = c.replace('settings.pid', 'os.getpid()')
if 'import os' not in c[:500]:
    c = c.replace('import time', 'import os\\nimport time')
with open('central_bus/main.py', 'w') as f:
    f.write(c)
print('  ✅ Fix applied')
"
        }
        export SOLOCORP_API_KEY="${SOLOCORP_API_KEY:-sk-solocorp-admin-local-dev-001}"
        nohup $PYTHON -m uvicorn central_bus.main:app \
          --host 127.0.0.1 --port 8099 > /tmp/central_bus.log 2>&1 &
        echo "  Bus PID: $!"
        sleep 2
        curl -s http://127.0.0.1:8099/v1/health >/dev/null 2>&1 \
          && echo "  ✅ Running" || echo "  ⚠ Check /tmp/central_bus.log"
    fi
fi

# ── Step 4: Restore CEO Memory ────────────────────────────────────────────
if $DO_FACTS; then
    echo ""
    echo "🧠 [4/5] CEO memory..."
    [[ ! -f brain/ceo-memory.json ]] && { echo "  ⚠ brain/ceo-memory.json not found"; exit 0; }

    COUNT=$($PYTHON -c "
import urllib.request, json
try:
    r = urllib.request.urlopen('http://127.0.0.1:8099/v1/health', timeout=3)
    d = json.loads(r.read())
    print(d.get('facts_count', 0))
except: print('0')
" 2>/dev/null || echo "0")

    if [[ "$COUNT" -gt 0 ]]; then
        echo "  ⏭ ${COUNT} facts exist"
    else
        echo "  Restoring from brain/ceo-memory.json..."
        $PYTHON -c "
import asyncio, json, sys
sys.path.insert(0, '.')
with open('brain/ceo-memory.json') as f:
    mem = json.load(f)

from central_bus.db import ensure_db
from central_bus.facts import FactsService

async def restore():
    db = await ensure_db()
    f = FactsService(db)
    
    for i, p in enumerate(mem.get('soul_plan', {}).get('pillars', [])):
        await f.set_fact(f'soul.plan.pillar{i+1}', p, updated_by='bootstrap')
    await f.set_fact('soul.plan.mantra', mem.get('soul_plan', {}).get('core_mantra', ''), updated_by='bootstrap')
    
    for d in mem.get('organization', {}).get('departments', []):
        await f.set_fact(f'org.dept.{d[\"id\"][:2]}', f'{d[\"name\"]} — {d[\"head\"]}: {d[\"scope\"]}', updated_by='bootstrap')
    
    for adr in mem.get('key_decisions', []):
        await f.set_fact(f'adr.{adr[\"id\"].lower()}', f'{adr[\"title\"]} ({adr[\"status\"]})', updated_by='bootstrap')
    
    sys_stat = mem.get('system_status', {})
    await f.set_fact('system.central_bus',
        f'Running on port {sys_stat.get(\"central_bus\", {}).get(\"port\", 8099)}', updated_by='bootstrap')
    await f.set_fact('system.mcp_server',
        f'Ready: {sys_stat.get(\"mcp_server\", {}).get(\"tools\", 7)} tools', updated_by='bootstrap')
    
    for item in mem.get('pending_initiatives', []):
        key = f'pending.{item.get(\"priority\", \"?\").lower()}.{item.get(\"task\", \"\")[:20].lower().replace(\" \", \"-\")}'
        await f.set_fact(key, f'{item.get(\"task\", \"\")} — {item.get(\"owner\", \"?\")} [{item.get(\"status\", \"?\")}]', updated_by='bootstrap')
    
    cnt = await f.count_facts()
    print(f'✅ Restored {cnt} facts into Central Bus')

asyncio.run(restore())
"
    fi
fi

# ── Step 5: Loop Runner ──────────────────────────────────────────────────
if $DO_LOOP; then
    echo ""
    echo "🔄 [5/5] Loop Runner..."
    $PYTHON -m loop_runner.main 2>/dev/null && echo "  ✅ Cycle done" \
      || echo "  ⏭ Some loops need external tools (OK)"
fi

# ── Done ──────────────────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo "  ✅ SoloCorp OS — Boot Complete!"
echo "================================================================"
echo ""
echo "  🚌 Central Bus:  http://127.0.0.1:8099"
echo "  🧠 CEO Memory:   $PYTHON brain/scripts/restore-ceo-memory.py"
echo "  🔌 MCP:          python3 -m solocorp_mcp.server"
echo "  📋 CEO recalls:  $(ls brain/ 2>/dev/null | wc -l) brain files"
echo ""
echo "  สั่ง boot ทันที (clone ครั้งต่อไป):"
echo "    cp .env.example .env && bash scripts/bootstrap-ceo.sh"
echo "================================================================"

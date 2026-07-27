#!/bin/bash
# SoloCorp OS — Start All Services (Grok / OpenCode / local)
# ใช้: bash scripts/start-services.sh
# ตรวจ: curl -s http://127.0.0.1:8099/v1/health

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

export PYTHONPATH="${REPO_DIR}${PYTHONPATH:+:$PYTHONPATH}"
export SOLOCORP_API_KEY="${SOLOCORP_API_KEY:-sk-solocorp-admin-local-dev-001}"

PY="${REPO_DIR}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "❌ Missing .venv — create with: python3 -m venv .venv && .venv/bin/pip install -r requirements-api.txt"
  exit 1
fi

is_up() {
  local url="$1"
  curl -sf -m 2 "$url" >/dev/null 2>&1
}

echo "🚀 Starting SoloCorp OS services..."
echo "=================================="
echo "   REPO: $REPO_DIR"
echo "   PYTHONPATH set · SOLOCORP_API_KEY present"
echo ""

# Central Bus (:8099)
if is_up "http://127.0.0.1:8099/v1/health"; then
  echo "📡 Central Bus (port 8099)... already up"
else
  echo -n "📡 Central Bus (port 8099)... "
  nohup "$PY" -m uvicorn central_bus.main:app \
    --host 127.0.0.1 --port 8099 > /tmp/central_bus.log 2>&1 &
  echo "PID $!"
  sleep 2
  if is_up "http://127.0.0.1:8099/v1/health"; then
    echo "   ✅ health ok"
  else
    echo "   ⚠️  not healthy yet — see /tmp/central_bus.log"
  fi
fi

# govctl API (:8765)
if is_up "http://127.0.0.1:8765/api/v1/health"; then
  echo "🏛  govctl API (port 8765)... already up"
else
  echo -n "🏛  govctl API (port 8765)... "
  if "$PY" -m govctl_cli api start >/tmp/govctl-api-start.log 2>&1; then
    echo "started"
  else
    # fallback: uvicorn if api start fails
    nohup "$PY" -m uvicorn govctl_cli.api.main:app \
      --host 127.0.0.1 --port 8765 > /tmp/govctl-api.log 2>&1 &
    echo "PID $! (uvicorn fallback)"
  fi
  sleep 1
fi

# Agent Worker
if pgrep -f "workers.agent_worker_service" >/dev/null 2>&1; then
  echo "🤖 Agent Worker... already running"
else
  echo -n "🤖 Agent Worker... "
  nohup "$PY" -m workers.agent_worker_service \
    > /tmp/agent_worker.log 2>&1 &
  echo "PID $!"
fi

sleep 1
echo ""
echo "✅ SoloCorp OS runtime ready for Grok"
echo "   Central Bus : http://127.0.0.1:8099/v1/health"
echo "   govctl API  : http://127.0.0.1:8765/api/v1/health"
echo "   Grok pack   : AGENTS.md + .grok/ (skills, agents, MCP)"
echo ""
echo "Next (Grok Build CLI):"
echo "   cd $REPO_DIR && source .venv/bin/activate && export PYTHONPATH=. && grok"
echo "   In TUI: /status  ·  /route <request>  ·  MCP tools solocorp_*"

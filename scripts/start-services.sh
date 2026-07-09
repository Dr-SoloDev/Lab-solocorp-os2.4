#!/bin/bash
# SoloCorp OS — Start All Services
# ใช้: bash scripts/start-services.sh

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

export SOLOCORP_API_KEY="sk-solocorp-admin-local-dev-001"

echo "🚀 Starting SoloCorp OS services..."
echo "=================================="

# Central Bus
echo -n "📡 Central Bus (port 8099)... "
nohup .venv/bin/python -m uvicorn central_bus.main:app \
  --host 127.0.0.1 --port 8099 > /tmp/central_bus.log 2>&1 &
echo "PID $!"

# Agent Worker
sleep 2
echo -n "🤖 Agent Worker... "
nohup .venv/bin/python -m workers.agent_worker_service \
  > /tmp/agent_worker.log 2>&1 &
echo "PID $!"

sleep 2
echo ""
echo "✅ Services started!"
echo "   Central Bus: http://127.0.0.1:8099"
echo "   Keys: cat /tmp/solocorp-keys.txt"

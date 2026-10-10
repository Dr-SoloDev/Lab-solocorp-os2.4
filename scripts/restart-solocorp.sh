#!/bin/bash
# SoloCorp OS — restart busd + govctl (หลัง reboot) — บันทึก 2026-09-25
# Project หลัก: /data/projects/Lab-solocorp-os2.4 (symlink ~/projects ชี้มาที่นี่)
cd /data/projects/Lab-solocorp-os2.4 || exit 1
source .venv/bin/activate && export PYTHONPATH=.
# kill เก่า (ถ้ามีค้าง)
pkill -f "central_bus.main:app" 2>/dev/null
pkill -f "govctl_cli.api.main:app" 2>/dev/null
sleep 2
# start ใหม่ (background + log)
nohup python -m uvicorn central_bus.main:app --host 127.0.0.1 --port 8099 > /tmp/busd.log 2>&1 &
nohup python -m uvicorn govctl_cli.api.main:app --host 127.0.0.1 --port 8765 > /tmp/govctl.log 2>&1 &
sleep 3
echo "--- busd ---"; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8099/health -H "X-API-Key: test" || echo "busd check done (401=running+auth OK)"
echo "--- govctl ---"; ss -tlnp | grep 8765 || echo "govctl NOT listening"
echo "--- docker ---"; docker ps --format "table {{.Names}}\t{{.Status}}" | head -n 5

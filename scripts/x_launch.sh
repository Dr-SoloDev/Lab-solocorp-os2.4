#!/usr/bin/env bash
# เปิด Chrome ตรงๆ ด้วยโปรไฟล์ถาวร + CDP port (คุมเองทั้งหมด)
set -uo pipefail

PROFILE="${X_PROFILE:-$HOME/.stealth-browser/profiles/x-solodev}"
PORT="${X_CDP_PORT:-9222}"
URL="${1:-https://x.com/compose/post}"
export DISPLAY="${DISPLAY:-:0}"

echo "โปรไฟล์: $PROFILE"
echo "CDP port: $PORT"
echo "URL: $URL"
echo "--- ล้าง lock เก่า ---"
rm -f "$PROFILE/SingletonLock" "$PROFILE/SingletonCookie" "$PROFILE/SingletonSocket" 2>/dev/null || true

nohup /opt/google/chrome/chrome \
  --user-data-dir="$PROFILE" \
  --remote-debugging-port="$PORT" \
  --remote-allow-origins='*' \
  --no-first-run --no-default-browser-check \
  --window-size=1280,1000 \
  --window-position=40,40 \
  "$URL" > /tmp/opencode/chrome.log 2>&1 &

sleep 6
echo "--- CDP ตอบไหม ---"
curl -s -m 5 "http://127.0.0.1:$PORT/json/version" | head -c 140
echo
echo "--- tabs ---"
curl -s -m 5 "http://127.0.0.1:$PORT/json/list" | python3 -c "
import sys,json
for t in json.load(sys.stdin):
    if t.get('type')=='page': print('  ', t.get('url','')[:90])
" 2>/dev/null | head -5

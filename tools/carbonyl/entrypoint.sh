#!/bin/sh
# carbonyl-read — รัน carbonyl ใน pty ขนาดคงที่ แล้ว dump raw ANSI stream
#
# ใช้โดย:  carbonyl-read <url>
# Env:     CARBONYL_WAIT (วินาที, default 12)
#           CARBONYL_COLS (default 120)
#           CARBONYL_ROWS (default 40)
#
# หมายเหตุ: carbonyl เป็น browser แบบ interactive จึงไม่จบเอง
#            เราจึงรอให้หน้าเว็บโหลดเสร็จ (WAIT) แล้วบังคับหยุด
set -u

URL="${1:-}"
[ -n "$URL" ] || { echo "usage: carbonyl-read <url>" >&2; exit 2; }

WAIT="${CARBONYL_WAIT:-12}"
COLS="${CARBONYL_COLS:-120}"
ROWS="${CARBONYL_ROWS:-40}"
OUT=/tmp/raw.txt

: > "$OUT"

# script สร้าง pty ให้ carbonyl ได้ (ไม่งั้น TIOCGWINSZ ได้ 0x0 → ได้แค่ 80x24)
# timeout กันไม่ให้ค้าง แล้ว cat สิ่งที่ได้ (บางส่วนอาจไม่ครบถ้าเว็บโหลดช้า)
if command -v timeout >/dev/null 2>&1; then
  timeout -s KILL "$WAIT" \
    script -q -c "stty rows $ROWS cols $COLS; /carbonyl/carbonyl --no-sandbox '$URL'" \
    /dev/null > "$OUT" 2>&1 || true
else
  script -q -c "stty rows $ROWS cols $COLS; /carbonyl/carbonyl --no-sandbox '$URL'" \
    /dev/null > "$OUT" 2>&1 &
  SPID=$!
  sleep "$WAIT"
  kill -9 "$SPID" 2>/dev/null || true
  sleep 1
fi

cat "$OUT"
exit 0

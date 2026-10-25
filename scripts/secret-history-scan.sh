#!/usr/bin/env bash
# 🔍 สแกน secret ทั้งประวัติ git — ไม่ใช่แค่ไฟล์วันนี้
#
# ทำไมต้องมี
# ──────────
# pre-commit hook ตรวจแค่ `git diff --cached` (ของใหม่) → คีย์ที่ commit ไปแล้ว
# hook มองไม่เห็นตลอดกาล (incident 2026-10-25: MAXPLUS key ใน docs/ ของ repo public
# และ hardcoded key ใน workers/llm_provider.py ที่ถูกลบไปแล้วแต่ยังอยู่ในประวัติ)
#
# ใช้
# ───
#   bash scripts/secret-history-scan.sh              # tracked files (HEAD) + history
#   bash scripts/secret-history-scan.sh --current    # เฉพาะ tracked files (เร็ว, ไม่กี่วิ)
#   bash scripts/secret-history-scan.sh --history    # เฉพาะประวัติ (~2 นาที)
#   bash scripts/secret-history-scan.sh --all        # + ไฟล์ที่ gitignore (ตรวจเครื่องตัวเอง)
#
# exit: 0 = ไม่มีค่าที่ต้องสงสัย · 1 = เจอ (ใช้ใน CI ได้)
# ปลอดภัย: พิมพ์แค่ 12 ตัวอักษรแรกของค่าที่เจอ — ไม่พิมพ์ secret เต็ม
#
# ค่าที่ "รู้ว่าเป็นของปลอม" อยู่ใน KNOWN_FAKE (ค่าทดสอบของ hook เอง + false positive
# จาก vendored venv) → รายงานเป็น ℹ️ ไม่ทำให้ exit 1

set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

# ── pattern ที่ถือว่าเป็น secret (fatal) ─────────────────────────────────
COMBINED='ccsk-[a-f0-9]{32,}|oc_sk_[A-Za-z0-9]{8,}|sk-[A-Za-z0-9_-]{32,}|ghp_[A-Za-z0-9]{36}|AKIA[0-9A-Z]{16}|[0-9]{8,10}:AA[A-Za-z0-9_-]{33}|-----BEGIN [A-Z ]*PRIVATE KEY-----'

# ── pattern เตือน (advisory, ไม่ทำให้ exit 1) ────────────────────────────
# จับ "การตั้งค่าแบบ ENV" ที่มีค่ายาว — ครอบคลุมกรณีที่ pattern ด้านบนไม่รู้จัก
# (เช่น LINE_CHANNEL_ACCESS_TOKEN) แต่ก็มีของ benign ปน (dev key, env var ref)
ADVISORY='[A-Z][A-Z0-9_]*(KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*[[:space:]]*[=:][[:space:]]*["'"'"']?[A-Za-z0-9_-]{20,}'

# ── ค่าที่รู้ว่าเป็นของปลอม/ตัวอย่าง (ไม่ต้อง rotate) ─────────────────────
KNOWN_FAKE=(
  'ccsk-1234567890abcdef'   # ค่าทดสอบของ scripts/test-api-key-protection.sh
  'ccsk-REDACTED'           # placeholder ที่เราใส่แทนค่าจริง
  'sk-1234567890'           # ค่าทดสอบ
  'sk-REDACTED'             # placeholder
  'AKIAAQAAAAAA'            # false positive ใน vendored PIL (ImageFont.py)
  'sk-where-roo'            # false positive ใน vendored psutil (_pslinux.py)
)

MODE="${1:-all-modes}"
FOUND=0
declare -a HEAD_VALUES=()
declare -a HISTORY_ONLY=()

mask() { printf '%s…' "$(printf '%s' "$1" | cut -c1-12)"; }

is_fake() {
  local v="$1" p
  for p in "${KNOWN_FAKE[@]}"; do
    [[ "$v" == "$p"* ]] && return 0
  done
  return 1
}

# ── 1. tracked files (HEAD) — พื้นที่เสี่ยงจริงของ repo ─────────────────
scan_head() {
  echo "== tracked files (HEAD) =="
  local out
  out=$(git grep -I -o -E "$COMBINED" -- . 2>/dev/null || true)
  if [ -z "$out" ]; then
    echo "  ✅ ไม่พบ pattern"
    return
  fi
  local path value
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    path=${line%%:*}
    value=${line#*:}
    if is_fake "$value"; then
      printf '  ℹ️  %-46s %s (ค่าปลอม/ตัวอย่าง)\n' "$path" "$(mask "$value")"
    else
      FOUND=1
      HEAD_VALUES+=("$value")
      printf '  🚨 %-46s %s\n' "$path" "$(mask "$value")"
    fi
  done <<< "$out"
}

# ── เติม HEAD_VALUES เงียบ ๆ (ใช้ในโหมด --history เพื่อไม่ให้ค่าที่อยู่ใน HEAD
#    ถูกเข้าใจผิดว่า "อยู่ในประวัติเท่านั้น")
collect_head_values() {
  local out line value
  out=$(git grep -I -o -E "$COMBINED" -- . 2>/dev/null || true)
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    value=${line#*:}
    is_fake "$value" || HEAD_VALUES+=("$value")
  done <<< "$out"
}

# ── 2. ประวัติทั้งหมด — หาค่าที่เคย commit แล้ว ──────────────────────────
scan_history() {
  echo "== git history ($(git rev-list --all --count) commits) =="
  local out
  out=$(git grep -I -o -E "$COMBINED" $(git rev-list --all) 2>/dev/null || true)
  if [ -z "$out" ]; then
    echo "  ✅ ไม่พบ pattern"
    return
  fi

  # commit:path:value → unique values + count
  local values
  values=$(printf '%s\n' "$out" | awk -F: '{v=$3; for(i=4;i<=NF;i++) v=v":"$i; print v}' | sort | uniq -c | sort -rn)

  local count value path_example in_head
  while read -r count value; do
    [ -z "$value" ] && continue
    if is_fake "$value"; then
      printf '  ℹ️  %-16s ×%-4s (ค่าปลอม/ตัวอย่าง)\n' "$(mask "$value")" "$count"
      continue
    fi

    # ยังอยู่ใน HEAD ไหม
    in_head="no"
    for hv in "${HEAD_VALUES[@]:-}"; do
      [[ "$hv" == "$value" ]] && in_head="yes" && break
    done

    # ไฟล์ที่เคยมีค่า (ตัวอย่าง 1 ไฟล์)
    path_example=$(printf '%s\n' "$out" | awk -F: -v v="$value" '{vv=$3; for(i=4;i<=NF;i++) vv=vv":"$i; if (vv==v) {print $2; exit}}')

    if [ "$in_head" = "yes" ]; then
      printf '  🚨 %-16s ×%-4s ยังอยู่ใน HEAD (%s)\n' "$(mask "$value")" "$count" "$path_example"
    else
      FOUND=1
      HISTORY_ONLY+=("$value|$count|$path_example")
      printf '  🟠 %-16s ×%-4s เฉพาะในประวัติ (%s) → ต้อง rotate\n' "$(mask "$value")" "$count" "$path_example"
    fi
  done <<< "$values"
}

# ── 3. ไฟล์ที่ gitignore (ตรวจเครื่องตัวเอง — .env ต้องมีค่าจริงเป็นปกติ) ──
scan_ignored() {
  echo "== ไฟล์ที่ gitignore (ไม่ขึ้น git — ตรวจสุขอนามัยเครื่อง) =="
  local hits
  hits=$(grep -rIoE --exclude-dir=.git --exclude-dir=.venv --exclude-dir=venv \
           --exclude-dir=node_modules --exclude-dir=bus \
           "$COMBINED" . 2>/dev/null | head -40 || true)
  if [ -z "$hits" ]; then
    echo "  ✅ ไม่พบ"
    return
  fi
  local tracked n_fake=0 n_real=0 path value
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    path=${line%%:*}; value=${line#*:}
    tracked="ignored"
    git ls-files --error-unmatch "$path" >/dev/null 2>&1 && tracked="TRACKED"
    if is_fake "$value"; then
      n_fake=$((n_fake + 1))
    else
      n_real=$((n_real + 1))
      [ "$tracked" = "TRACKED" ] && FOUND=1
      printf '  %s %-44s %s (%s)\n' \
        "$([ "$tracked" = "TRACKED" ] && echo 🚨 || echo ℹ️)" \
        "$path" "$(mask "$value")" "$tracked"
    fi
  done <<< "$hits"
  echo "  ℹ️  ค่าจริงในไฟล์ที่ gitignore: $n_real · ค่าปลอม: $n_fake (ไม่ขึ้น git = ไม่รั่ว)"
}

# ── 4. เตือน: การตั้งค่าแบบ ENV ที่มีค่ายาว (ไม่ fatal) ───────────────────
scan_advisory() {
  echo "== advisory: ENV-style assignments ที่มีค่ายาว (tracked files) =="
  local out line
  out=$(git grep -I -o -E "$ADVISORY" -- . 2>/dev/null || true)
  if [ -z "$out" ]; then
    echo "  ✅ ไม่พบ"
    return
  fi
  local known
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    known="review"
    case "$line" in
      *sk-solocorp-admin-local-dev-001*) known="dev key ที่ประกาศไว้ (ไม่ใช่ secret)" ;;
      *ccsk-REPLACE_WITH_NEW_KEY*)       known="placeholder" ;;
      *ccsk-1234567890abcdef*)           known="ค่าทดสอบ" ;;
      *your-maxplus-api-key-here*)       known="placeholder" ;;
      *GITHUB_WEBHOOK_SECRET*)           known="ชื่อ env var (ไม่มีค่า)" ;;
    esac
    printf '  %s %-58s %s\n' \
      "$([ "$known" = "review" ] && echo ⚠️ || echo ℹ️)" \
      "$(printf '%s' "${line:0:58}")" "$known"
  done <<< "$out"
  echo "  ℹ️  advisory ไม่ทำให้ exit 1 — เปิดดูด้วยคนว่าเป็นค่าจริงหรือไม่"
}

case "$MODE" in
  --current) scan_head; echo; scan_advisory ;;
  --history) collect_head_values; scan_history ;;
  --all)     scan_head; echo; scan_history; echo; scan_ignored; echo; scan_advisory ;;
  *)         scan_head; echo; scan_history ;;
esac

echo
if [ "$FOUND" -eq 0 ]; then
  echo "✅ ไม่พบ secret ที่ต้อง rotate"
  exit 0
fi

echo "🚨 พบ secret ที่ต้องจัดการ:"
if [ "${#HEAD_VALUES[@]}" -gt 0 ]; then
  echo "   · ยังอยู่ในไฟล์ปัจจุบัน → แทนด้วย placeholder + rotate ที่ต้นทาง"
fi
for item in "${HISTORY_ONLY[@]:-}"; do
  [ -z "$item" ] && continue
  IFS='|' read -r v c p <<< "$item"
  echo "   · $(mask "$v") เฉพาะในประวัติ (×$c, $p) → rotate ทันที; จะลบประวัติต้องได้ Owner อนุมัติ"
done
echo
echo "   ⚠️ การลบในไฟล์ไม่ทำให้ค่าที่เคย public ใช้ไม่ได้ — rotate ก่อน แล้วค่อยพิจารณา history rewrite"
exit 1

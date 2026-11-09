#!/usr/bin/env bash
# Restart the SoloCorp MCP generation cleanly.
#
# Problem this solves: an MCP server loads its modules once at startup, so
# every edit after that is invisible to the process. Restarting by asking the
# host to reconnect is not enough when old generations are still running —
# on 2026-11-02 six generations were alive at once (one from the previous
# day) and which one answered depended on luck.
#
# This script finds every `python3 -m axis_mcp.*` process, shows its start
# time and whether it is older than the newest source file, and only kills
# when asked. The host respawns a fresh generation on the next tool call.
#
# Usage:
#   scripts/restart-mcp.sh              # report only (safe, default)
#   scripts/restart-mcp.sh --yes        # kill every axis_mcp process
#   scripts/restart-mcp.sh --yes --stale-only
#
# Never touches: busd (uvicorn central_bus.main:app), the shell, or this file.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DO_KILL=0
STALE_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --yes|-y) DO_KILL=1 ;;
    --stale-only) STALE_ONLY=1 ;;
    --help|-h)
      sed -n '2,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "unknown option: $arg (try --help)" >&2
      exit 2
      ;;
  esac
done

command -v ps >/dev/null || { echo "ps not available" >&2; exit 1; }

HEAD_SHORT="$(git rev-parse --short HEAD 2>/dev/null || echo 'no-git')"
NEWEST_SRC="$(find axis_mcp -name '*.py' -not -path '*/__pycache__/*' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1)"
NEWEST_SRC_EPOCH="${NEWEST_SRC%% *}"
NEWEST_SRC_PATH="${NEWEST_SRC#* }"
if [[ -z "${NEWEST_SRC_EPOCH:-}" ]]; then
  echo "cannot read source mtimes under axis_mcp/" >&2
  exit 1
fi

fmt_epoch() { date -d "@$1" '+%m-%d %H:%M:%S' 2>/dev/null || echo "?"; }

echo "SoloCorp MCP restart check"
echo "  repo HEAD        : $HEAD_SHORT"
echo "  newest source    : $(fmt_epoch "$NEWEST_SRC_EPOCH")  ${NEWEST_SRC_PATH:-none}"
echo

# pid, args, start epoch for every axis_mcp server process
mapfile -t ROWS < <(
  ps -eo pid=,args= \
    | grep -E -- '-m axis_mcp\.' \
    | grep -v -E 'grep|restart-mcp' \
    | while read -r pid rest; do
        [[ -d "/proc/$pid" ]] || continue
        start="$(stat -c %Y "/proc/$pid" 2>/dev/null || echo 0)"
        cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | sed 's|.*python3\{0,1\} ||' | cut -c1-58)"
        echo "$pid|$start|$cmd"
      done | sort -t'|' -k2,2n
)

if [[ ${#ROWS[@]} -eq 0 ]]; then
  echo "No axis_mcp process is running."
  echo "The host will start one on the next tool call."
  exit 0
fi

printf '%-7s %-15s %-9s %-8s %s\n' PID STARTED AGE STATE COMMAND
TARGETS=()
STALE=0
for row in "${ROWS[@]}"; do
  IFS='|' read -r pid start cmd <<< "$row"
  age_s=$(( $(date +%s) - start ))
  age_h=$(( age_s / 3600 ))
  age_m=$(( (age_s % 3600) / 60 ))
  age="${age_h}h${age_m}m"
  # Same tolerance as axis_mcp/runtime_freshness.py
  if awk -v s="$start" -v n="$NEWEST_SRC_EPOCH" 'BEGIN{exit !(n > s + 1)}'; then
    state="STALE"
    STALE=$((STALE + 1))
  else
    state="current"
  fi
  printf '%-7s %-15s %-9s %-8s %s\n' "$pid" "$(fmt_epoch "$start")" "$age" "$state" "$cmd"
  if [[ "$STALE_ONLY" -eq 1 && "$state" != "STALE" ]]; then
    continue
  fi
  TARGETS+=("$pid")
done

echo
echo "generations: ${#ROWS[@]}   stale: $STALE   target: ${#TARGETS[@]}"

BUSDS="$(ps -eo pid=,args= | grep -E 'uvicorn central_bus\.main:app' | grep -v grep || true)"
if [[ -n "$BUSDS" ]]; then
  echo "busd (not touched) :"
  echo "$BUSDS" | awk '{printf "  pid %s\n", $1}'
fi

if [[ "$DO_KILL" -ne 1 ]]; then
  echo
  echo "DRY RUN — nothing killed. Re-run with --yes to restart cleanly."
  exit 0
fi

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo
  echo "Nothing to kill."
  exit 0
fi

echo
echo "Sending TERM to: ${TARGETS[*]}"
for pid in "${TARGETS[@]}"; do
  kill -TERM "$pid" 2>/dev/null || true
done

# Give them up to 5s to exit, then insist.
for _ in 1 2 3 4 5; do
  alive=0
  for pid in "${TARGETS[@]}"; do
    [[ -d "/proc/$pid" ]] && alive=1
  done
  [[ "$alive" -eq 0 ]] && break
  sleep 1
done

for pid in "${TARGETS[@]}"; do
  if [[ -d "/proc/$pid" ]]; then
    echo "  pid $pid ignored TERM -> KILL"
    kill -KILL "$pid" 2>/dev/null || true
  fi
done
sleep 1

LEFT=0
for pid in "${TARGETS[@]}"; do
  [[ -d "/proc/$pid" ]] && { echo "  still alive: $pid" >&2; LEFT=1; }
done

if [[ "$LEFT" -ne 0 ]]; then
  echo "Some processes survived the restart." >&2
  exit 1
fi

echo "All targeted generations are gone."
echo "Next tool call starts a fresh generation, which will then report"
echo "  runtime.status = current   (process newer than every source file)"

"""Verdict log v0 — append-only evidence of every gate decision.

Why this exists (backtest v2, 2026-10-10): state.db keeps latest run only,
so TTD / catch-rate / weekly noise had no raw material. Every day without
this log is data never recoverable.

Design rules:
- ADDITIVE only: new file writes, never changes loop behavior.
- FAIL-SAFE: telemetry must not break product — write errors go to stderr,
  never raise. (Deliberate contrast to media_daily's `except: pass` bug:
  there the swallow hid a broken gate; here the guarded region is the
  *telemetry write itself*, and the swallow is documented + visible.)
- Verdicts: PASS / FAIL / SKIP / NOT_DUE (NOT_DUE doubles as per-gate heartbeat).
- Tiers (Owner 2026-10-10): T1 = none until Owner designates; default T2;
  subscription_audit = T3 (advisory). Tier binds to reversibility axis.
- Fingerprint v1: (version, class). input_hash reserved (None in v0,
  per-loop enrichment follows).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
VDIR = BASE / "bus" / "verdicts"

NORMALIZER_VERSION = 1

TIERS = {
    "subscription_audit": "T3",
}
DEFAULT_TIER = "T2"  # new gates default T2; T1 requires Owner designation


def fingerprint(reason: str) -> str:
    """v1: strip instance tokens, keep class tokens (errno kept on purpose:
    Errno 111 vs 113 are different diseases)."""
    s = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+\d:]*", "<TS>", reason)
    s = re.sub(r"0x[0-9a-fA-F]+", "<HEX>", s)
    s = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b", "<IP>", s)
    s = re.sub(r"msg-\d+-\d+", "<ID>", s)
    return s.strip()[:300]


def infer_verdict(result: str) -> str:
    """v0 heuristic from result-string prefixes (loops use consistent markers).
    Per-loop explicit verdicts follow; this is documented scaffolding, not law."""
    t = (result or "").lstrip()
    if t.startswith("⏭"):
        return "SKIP"
    if t.startswith("⚠️") or "❌" in t[:50]:
        return "FAIL"
    return "PASS"


def append_verdict(loop_id: str, verdict: str, detail: str = "",
                   input_hash: str | None = None) -> None:
    """Append one verdict line. Never raises (fail-safe telemetry)."""
    try:
        VDIR.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).astimezone().date().isoformat()
        reason = fingerprint(detail) if verdict in ("SKIP", "FAIL") else "pass"
        line = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "loop_id": loop_id,
            "verdict": verdict,
            "tier": TIERS.get(loop_id, DEFAULT_TIER),
            "fp_version": NORMALIZER_VERSION,
            "fingerprint": reason,
            "input_hash": input_hash,
            "detail": (detail or "")[:300],
        }
        with open(VDIR / f"{day}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception as e:  # fail-safe: telemetry failure must not break loops
        print(f"[verdict-log] write failed for {loop_id}: {e}", file=sys.stderr)

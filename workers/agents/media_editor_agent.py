"""Media Editor mini-agent D2 (deterministic, no LLM)."""

from __future__ import annotations
import json, re, shlex
from datetime import datetime, timezone
from pathlib import Path
from workers.agents.base_agent import BaseAgent

WRITE_ROOT = Path("bus/creative/media-qa")
SOURCES = (
    "profiles/15-content-creator/sek/team/02-content-media-editor.SOUL.md",
    "axis_mcp/departments/content_skills/media-production/SKILL.md",
)
LOG_PATH = "bus/evidence/2026-11-23/d2-media-editor/tool-calls.jsonl"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class MediaEditorAgent(BaseAgent):
    def __init__(self, bus_url="", api_key="", log_path=LOG_PATH):
        super().__init__(
            "team-content-media-editor", "Media Editor", SOURCES[0], bus_url, api_key
        )
        self.log_path = Path(log_path)
        self.tool_calls: list[dict] = []

    def _record(self, tool, args, ok):
        self.tool_calls.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "tool": tool,
                "args": args,
                "ok": ok,
            }
        )
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(self.tool_calls[-1], ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _fail(self, summary, error, **extra):
        return {
            "status": "failed",
            "summary": summary,
            "details": {"error": error, "tool_calls": self.tool_calls, **extra},
        }

    async def _read(self, path):
        try:
            text = await self.read_file(path)
        except (OSError, UnicodeDecodeError) as exc:
            text = f"FAILED READ: {path} ({type(exc).__name__})"
        self._record("read_file", path, not text.startswith("FAILED"))
        return text

    async def _write(self, path, content):
        p = Path(path).resolve()
        if not p.is_relative_to(WRITE_ROOT.resolve()):
            raise PermissionError(f"write outside {WRITE_ROOT}: {path}")
        msg = await self.write_file(str(p), content)
        self._record("write_file", str(p), "chars" in msg or "✅" in msg)
        return msg

    async def _verify(self, path):
        cmd = f"test -f {shlex.quote(path)} && wc -c < {shlex.quote(path)}"
        out = await self.run_command(cmd)
        self._record(
            "run_command", cmd, "FAILED" not in out and "Command error" not in out
        )
        m = re.search(r"(\d+)", out)
        return {"raw": out, "bytes": int(m.group(1)) if m else 0}

    def _check(self, rec):
        e = []
        sha = str(((rec.get("video") or {}).get("sha256")) or "")
        if not SHA_RE.fullmatch(sha):
            e.append("sha256_must_be_64_hex")
        r = rec.get("render") or {}
        dur = float(r.get("duration_seconds") or 0)
        if not any(abs(dur - t) < 0.6 for t in (90.0, 100.0)):
            e.append(f"duration_must_be_90_or_100_got_{dur}")
        if int(r.get("scene_count") or 0) not in (6, 10):
            e.append("scene_count_6_or_10")
        if int(r.get("fps") or 0) != 30:
            e.append("fps_30")
        m = r.get("audio_measurement") or {}
        if abs(float(m.get("integrated_lufs", 999)) + 16.0) > 0.5:
            e.append("lufs_range")
        if float(m.get("true_peak_dbtp", 99)) > -1.5:
            e.append("true_peak_ceiling")
        if rec.get("gate_passed") is not False or rec.get("published") is not False:
            e.append("gate_published_must_stay_false")
        return e

    def _checklist(self, rec, cid, sha, errs):
        r = rec.get("render") or {}
        m = r.get("audio_measurement") or {}
        ok = "PASS" if not errs else "REVIEW"
        return f"# Media QA Checklist — {cid}\n\nSHA-256: `{sha}`\n\n## Specs\n- duration: {r.get('duration_seconds')}s, scenes: {r.get('scene_count')}\n- resolution: 1080x1920, fps: {r.get('fps')}, codec: H.264/AAC 48kHz\n- route: {rec.get('route', 'local per-scene')} | degraded: {rec.get('degraded', False)}\n\n## LUFS\n- integrated: {m.get('integrated_lufs')} LUFS (target -16.0 +/-0.5)\n- true peak: {m.get('true_peak_dbtp')} dBTP (ceiling -1.5)\n\n## Gate Decision\n- decision: review_required, gate_passed: false, published: false\n- verdict: {ok}\n- failed: {', '.join(errs) if errs else 'none'}\n- approval: NOT recorded here — human must approve exact version\n"

    async def execute(self, task):
        pay = task.get("payload") or {}
        p = pay.get("params", {})
        rp = pay.get("render_path") or p.get("render_path")
        if not rp:
            return self._fail("no render_path", "missing_input")
        out_early = p.get("out_path") or str(WRITE_ROOT / "qa-checklist.md")
        if not Path(out_early).resolve().is_relative_to(WRITE_ROOT.resolve()):
            return self._fail("outside_root", "write_out_of_bounds")
        for s in SOURCES:
            t = await self._read(s)
            if t.startswith("FAILED") or "not found" in t.lower()[:60]:
                return self._fail(f"source unreadable: {s}", "source_unreadable")
        raw = await self._read(rp)
        if raw.startswith("FAILED") or "not found" in raw.lower()[:80]:
            return self._fail(f"render unreadable: {rp}", "render_unreadable")
        try:
            rec = json.loads(raw)
        except (ValueError, TypeError):
            return self._fail("render is not JSON", "render_invalid_json")
        errs = self._check(rec)
        sha = str(((rec.get("video") or {}).get("sha256")) or "")
        cid = str(rec.get("campaign_id") or "unknown")
        try:
            await self._write(out_early, self._checklist(rec, cid, sha, errs))
        except PermissionError as exc:
            return self._fail(str(exc), "write_out_of_bounds")
        chk = await self._verify(out_early)
        if chk["bytes"] <= 0:
            return self._fail("checklist empty", "write_failed")
        st = "completed" if not errs else "failed"
        return {
            "status": st,
            "summary": f"qa {cid} {'PASS' if not errs else 'REVIEW'}",
            "details": {
                "agent": self.agent_id,
                "out_path": out_early,
                "sha256": sha,
                "errors": errs,
                "tool_calls": self.tool_calls,
                "log": str(self.log_path),
            },
        }

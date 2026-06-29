import re
import subprocess
from datetime import timedelta
from pathlib import Path
from ..runner import Loop


def _run(script: str, op: str) -> str:
    r = subprocess.run(
        [str(Path.home() / ".local/bin" / script), op],
        capture_output=True, text=True, timeout=10,
    )
    return r.stdout.strip() if r.returncode == 0 else ""


def _extract(text: str, pattern: str) -> str:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else "N/A"


class DailyBriefLoop(Loop):
    loop_id = "daily_brief"
    interval = timedelta(hours=20)
    trust_level = 1  # L1 report only
    model_hint = "glm-5.2"  # cron — cheap model for structured data fetch

    def run(self) -> str:
        summary_txt = _run("mcp-fallback-finance", "get_summary")
        runway_txt  = _run("mcp-fallback-finance", "get_runway")
        inbox_txt   = _run("mcp-fallback-brain", "read_inbox")

        cash     = _extract(summary_txt, r"คงเหลือ:\s*([\d,\.]+\s*บาท)")
        income   = _extract(summary_txt, r"รายรับ:\s*([\d,\.]+\s*บาท)")
        expense  = _extract(summary_txt, r"รายจ่าย:\s*([\d,\.]+\s*บาท)")
        runway   = _extract(runway_txt,  r"Runway:\s*([\d\.]+)\s*เดือน")

        lines = [
            "## CEO Morning Brief",
            f"💰 Cash: {cash} | รายรับ: {income} | รายจ่าย: {expense}",
            f"📆 Runway: {runway} เดือน",
        ]

        try:
            if float(runway) < 6:
                lines.append(f"🚨 CRITICAL: Runway {runway} เดือน — ต่ำกว่า 6 เดือน! escalate meetoo ทันที")
        except (ValueError, TypeError):
            pass

        # Brain inbox summary (count lines with content)
        inbox_items = [l for l in inbox_txt.splitlines() if l.strip() and not l.startswith("📥")]
        if inbox_items:
            lines.append(f"📥 Inbox: {len(inbox_items)} items")

        return "\n".join(lines)

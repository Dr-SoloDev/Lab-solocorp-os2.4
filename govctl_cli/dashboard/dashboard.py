"""
govctl dashboard — Terminal-based SoloCorp OS Pipeline Dashboard.

Renders project state, agent status, governance counts, and recent events
to the terminal using the Rich library (fallback to plain text).

Usage:
    govctl dashboard              — One-shot summary
    govctl dashboard --watch      — Live-updating dashboard (every 5s)
"""

from __future__ import annotations

import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from govctl_cli.monitor import collect_metrics, list_projects

# ── Try importing Rich for beautiful terminal output ──

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich import box

    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False


# ===========================================================================
# Plain-text renderers (fallback when Rich is not available)
# ===========================================================================

def _plain_divider(title: str = "", width: int = 55) -> str:
    if title:
        return f"─── {title} " + "─" * (width - len(title) - 5)
    return "─" * width


def render_plain(metrics: dict, projects: list[dict]) -> str:
    """Render a plain-text dashboard to a string."""
    lines: list[str] = []
    w = 55

    lines.append("")
    lines.append(f"  SoloCorp OS — Pipeline Dashboard  ".center(w, "─"))
    lines.append("")

    # Summary stats
    lines.append(f"  Active Projects:  {metrics.get('active_projects', 0)}")
    lines.append(f"  Queued Messages:  {metrics.get('total_queued', 0)}")
    queued = metrics.get("queued_messages", {})
    q_details = "  ".join(f"{k}={queued.get(k, 0)}" for k in ("critical", "high", "normal", "low"))
    lines.append(f"    ({q_details})")
    lines.append(f"  Agents Available: {metrics.get('agent_count', 5)}/5")
    lines.append(f"  ADRs: {metrics.get('adr_count', 0)}   RFCs: {metrics.get('rfc_count', 0)}   Guards: {metrics.get('guard_count', 0)}")
    lines.append("")

    # Project pipeline
    if projects:
        lines.append(_plain_divider("Projects"))
        for p in projects:
            pct = p.get("progress_pct", 0)
            bar_len = 20
            filled = round(bar_len * pct / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            lines.append(f"  {p.get('name', p['project_id']):<20} [{bar}] {pct:>3}%  {p.get('phase', ''):>10}  {p.get('status', '')}")
    else:
        lines.append("  No projects.")

    lines.append("")
    lines.append(_plain_divider("Recent Events"))
    events = metrics.get("recent_events", [])
    if events:
        for evt in events[:8]:
            ts = evt.get("ts", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    ts_short = f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
                except (ValueError, TypeError):
                    ts_short = ts[-8:] if len(ts) >= 8 else ts
            else:
                ts_short = ""
            ev = evt.get("event", "?")
            pid = evt.get("project_id", "") or evt.get("artifact_id", "") or ""
            lines.append(f"  · {ev:<25} {pid:<20} {ts_short}")
    else:
        lines.append("  No recent events.")

    lines.append("")
    lines.append("─" * w)
    ts = metrics.get("timestamp", datetime.now(timezone.utc).isoformat())
    lines.append(f"  Last updated: {ts}")

    return "\n".join(lines)


# ===========================================================================
# Rich renderers (premium terminal output)
# ===========================================================================

def build_rich_layout(metrics: dict, projects: list[dict]) -> Panel:
    """Build a Rich Panel containing the full dashboard."""
    if not RICH_AVAILABLE:
        return None  # type: ignore[return-value]

    rows: list = []

    # ── Summary row ──
    queued = metrics.get("queued_messages", {})
    summary = Table.grid(padding=(0, 2))
    summary.add_row(
        f"Active Projects: [bold cyan]{metrics.get('active_projects', 0)}",
        f"Queued Messages: [bold yellow]{metrics.get('total_queued', 0)}",
        f"Agents Available: [bold green]{metrics.get('agent_count', 5)}/5",
    )
    q_detail = "Critical: [red]{}[/]  High: [yellow]{}[/]  Normal: [blue]{}[/]  Low: [dim]{}[/]".format(
        queued.get("critical", 0), queued.get("high", 0),
        queued.get("normal", 0), queued.get("low", 0),
    )
    summary.add_row(
        f"ADRs: [bold cyan]{metrics.get('adr_count', 0)}",
        f"RFCs: [bold magenta]{metrics.get('rfc_count', 0)}",
        f"Guards: [bold green]{metrics.get('guard_count', 0)}",
    )
    summary.add_row(q_detail)
    rows.append(summary)
    rows.append("")

    # ── Project pipeline ──
    if projects:
        proj_table = Table(
            box=box.SIMPLE,
            title="Pipeline Projects",
            title_style="bold",
            padding=(0, 1),
        )
        proj_table.add_column("Project", style="cyan", no_wrap=True)
        proj_table.add_column("Progress", justify="right")
        proj_table.add_column("Phase", style="magenta")
        proj_table.add_column("Status", style="green")

        for p in projects:
            pct = p.get("progress_pct", 0)
            bar_len = 20
            filled = round(bar_len * pct / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            proj_table.add_row(
                p.get("name", p["project_id"])[:25],
                f"{bar} {pct:>3}%",
                p.get("phase", ""),
                p.get("status", ""),
            )
        rows.append(proj_table)
    else:
        rows.append("[dim]No projects in pipeline.[/]")

    rows.append("")

    # ── Recent events ──
    events = metrics.get("recent_events", [])
    if events:
        evt_table = Table(
            box=box.SIMPLE,
            title="Recent Events",
            title_style="bold",
            padding=(0, 1),
        )
        evt_table.add_column("Event", style="yellow", no_wrap=True)
        evt_table.add_column("Project", style="cyan")
        evt_table.add_column("Time", style="dim", no_wrap=True)

        for evt in events[:8]:
            ts = evt.get("ts", "")
            ts_short = ""
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    ts_short = f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
                except (ValueError, TypeError):
                    ts_short = ts[-8:] if len(ts) >= 8 else ts
            evt_table.add_row(
                evt.get("event", "?")[:28],
                (evt.get("project_id", "") or evt.get("artifact_id", "") or "")[:20],
                ts_short,
            )
        rows.append(evt_table)
    else:
        rows.append("[dim]No recent events.[/]")

    layout = Table.grid()
    for row in rows:
        if isinstance(row, str):
            layout.add_row(Text(row))
        else:
            layout.add_row(row)

    panel = Panel(
        layout,
        title="[bold blue]SoloCorp OS — Pipeline Dashboard[/]",
        border_style="blue",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    return panel


def render_dashboard() -> None:
    """Render a one-shot dashboard to stdout."""
    try:
        metrics = collect_metrics()
    except Exception:
        metrics = {}

    try:
        projects = list_projects()
    except Exception:
        projects = []

    if not metrics and not projects:
        print("Dashboard: no metrics available yet")
        return

    if RICH_AVAILABLE:
        panel = build_rich_layout(metrics, projects)
        console.print(panel)
    else:
        print(render_plain(metrics, projects))


def run_dashboard(watch: bool = False, interval: float = 5.0) -> None:
    """Run the dashboard, optionally in live-update mode.

    Args:
        watch: If True, re-render every *interval* seconds.
        interval: Seconds between updates (default 5.0).
    """
    if not RICH_AVAILABLE and watch:
        print("Rich library required for watch mode. Install it with: pip install rich")
        sys.exit(1)

    if watch and RICH_AVAILABLE:
        with Live(
            auto_refresh=False,
            console=console,
            screen=True,
        ) as live:
            try:
                while True:
                    metrics = collect_metrics()
                    projects = list_projects()
                    panel = build_rich_layout(metrics, projects)
                    live.update(panel, refresh=True)
                    time.sleep(interval)
            except KeyboardInterrupt:
                console.print("\n[yellow]Dashboard stopped.[/]")
    else:
        render_dashboard()


# ===========================================================================
# CLI entry point (used by govctl dashboard command)
# ===========================================================================

def cmd_dashboard(
    watch: bool = False,
    interval: float = 5.0,
) -> None:
    """CLI callable — render or watch the dashboard."""
    run_dashboard(watch=watch, interval=interval)

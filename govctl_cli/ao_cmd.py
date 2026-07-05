"""
govctl AO commands — ``govctl ao list``, ``govctl ao run``, ``govctl ao status``.

Registered as a sub-app in the main govctl CLI.
"""

from __future__ import annotations

import sys
import json
import typer
from pathlib import Path
from typing import Optional

from .ao import (
    REGISTRY,
    get_adapter,
    list_agents,
    check_ao,
    get_ao_status,
    run_agent,
    AOClient,
)

ao_app = typer.Typer(name="ao", help="Agent Orchestrator — invoke AO agents")

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@ao_app.command()
def list():
    """List available AO agent adapters with descriptions."""
    agents = list_agents()

    if not agents:
        typer.echo("⚠️  No AO agents registered.")
        raise typer.Exit()

    typer.echo(f"🧠 AO Agents ({len(agents)} registered)")
    typer.echo("─" * 60)
    for a in agents:
        typer.echo(f"  {a['agent_id']:<15} {a['display_name']}")
        if a["description"]:
            typer.echo(f"  {'':<15} {a['description']}")
        typer.echo()

    # Show CLI status
    cli_ok = check_ao()
    cli_status = "✓ available" if cli_ok else "✗ NOT FOUND"
    typer.echo(f"AO CLI: {cli_status}")


@ao_app.command()
def map(
    profile_id: str = typer.Argument(
        ..., help="Profile ID, e.g. 07-engineering or 02-cfo",
    ),
):
    """Show which AO agent a profile maps to."""
    try:
        from .ao.agents import get_agent_for_profile
        from .ao.adapter import get_adapter

        agent_id = get_agent_for_profile(profile_id)
        adapter = get_adapter(agent_id)

        typer.echo(f"Profile:      {profile_id}")
        typer.echo(f"AO Agent:     {agent_id}")
        typer.echo(f"Display Name: {adapter.display_name}")

    except KeyError as exc:
        typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(code=1)
    except ImportError as exc:
        typer.echo(f"❌ AO module error: {exc}", err=True)
        raise typer.Exit(code=1)


@ao_app.command()
def run(
    agent_id: str = typer.Argument(
        ..., help="Agent ID (ceo, orchestrator, architect, engineering, qa)",
    ),
    task: str = typer.Option("", "--task", "-t", help="Task description (inline)"),
    project: str = typer.Option("default", "--project", "-p", help="Project ID"),
    phase: str = typer.Option("general", "--phase", help="Project phase"),
    prompt_file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Read task prompt from file",
    ),
    json_input: Optional[str] = typer.Option(
        None, "--json", help="JSON context (inline)",
    ),
    timeout: int = typer.Option(300, "--timeout", help="Max seconds to wait"),
    raw: bool = typer.Option(False, "--raw", help="Output raw response without formatting"),
):
    """Run a single AO agent with the given task prompt."""
    # Validate agent
    if agent_id not in REGISTRY:
        typer.echo(f"❌ Unknown agent: {agent_id!r}", err=True)
        typer.echo(f"   Available: {', '.join(sorted(REGISTRY.keys()))}", err=True)
        raise typer.Exit(code=1)

    # Build context
    context: dict = {
        "project_id": project,
        "phase": phase,
    }

    # Priority: --json > --file > --task > stdin
    if json_input:
        try:
            context.update(json.loads(json_input))
        except json.JSONDecodeError as exc:
            typer.echo(f"❌ Invalid JSON: {exc}", err=True)
            raise typer.Exit(code=1)
    elif prompt_file:
        if not prompt_file.exists():
            typer.echo(f"❌ File not found: {prompt_file}", err=True)
            raise typer.Exit(code=1)
        context["task"] = prompt_file.read_text().strip()
    elif task:
        context["task"] = task
    elif not sys.stdin.isatty():
        # Read piped input
        context["task"] = sys.stdin.read().strip()
    else:
        # Interactive prompt
        typer.echo(f"Enter task for agent '{agent_id}':")
        context["task"] = typer.prompt_text("").strip()

    if not context.get("task"):
        typer.echo("❌ No task provided.", err=True)
        raise typer.Exit(code=1)

    # Run agent
    typer.echo(f"🚀 Running agent '{agent_id}' (project={project}, phase={phase}) …",
               err=True)

    result = run_agent(agent_id, context, timeout=timeout)

    if raw:
        typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _format_result(agent_id, result)


@ao_app.command()
def status():
    """Check AO CLI availability and agent registry status."""
    status = get_ao_status()

    typer.echo("🧠 AO Status")
    typer.echo("─" * 40)

    # CLI availability
    if status["cli_available"]:
        typer.echo(f"✓ AO CLI:     available ({status['cli_path']})")
    else:
        typer.echo(f"✗ AO CLI:     NOT FOUND ({status['cli_path']})")
        typer.echo(f"  Set AO_CLI_PATH env var or pass --cli-path to override")

    typer.echo(f"  Agents:      {status['agent_count']} registered")

    for a in status["agents"]:
        typer.echo(f"    - {a['agent_id']:<15} {a['display_name']}")

    # Bridge status
    try:
        from .ao.bridge import daemon_status
        bridge = daemon_status()
        if bridge["running"]:
            typer.echo(f"✓ AO bridge:  running (PID {bridge['pid']})")
        else:
            typer.echo(f"✗ AO bridge:  not running")
    except ImportError:
        typer.echo(f"~ AO bridge:  unavailable")


@ao_app.command()
def bridge(
    action: str = typer.Argument(
        ..., help="start | stop | status | process",
    ),
    detach: bool = typer.Option(True, "--detach/--foreground", help="Run as daemon"),
    batch: int = typer.Option(5, "--batch", "-b", help="Messages to process (one-shot)"),
):
    """Manage the AO bridge daemon (Central Bus ↔ AO)."""
    try:
        from .ao.bridge import cmd_start, cmd_stop, cmd_status, cmd_process
    except ImportError as exc:
        typer.echo(f"❌ AO bridge unavailable: {exc}", err=True)
        raise typer.Exit(code=1)

    if action == "start":
        cmd_start(detach=detach)
    elif action == "stop":
        cmd_stop()
    elif action == "status":
        result = cmd_status()
        if result.get("running"):
            typer.echo(f"✓ AO bridge is running (PID {result['pid']})")
        else:
            typer.echo("✗ AO bridge is not running")
    elif action == "process":
        count = cmd_process(batch_size=batch)
        typer.echo(f"Processed {count} AO_REQUEST message(s)")
    else:
        typer.echo(f"❌ Unknown action: {action!r} (use: start, stop, status, process)",
                   err=True)
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------


def _format_result(agent_id: str, result: dict) -> None:
    """Pretty-print an agent result to stdout."""
    status = result.get("status", "unknown")
    symbol = "✓" if status == "success" else "✗"
    typer.echo(f"\n{symbol} Agent '{agent_id}' — status: {status}")

    if status == "error":
        typer.echo(f"  Error: {result.get('error', 'Unknown error')}")
        return

    # Print agent-specific fields
    if agent_id == "ceo":
        typer.echo(f"\n  Assessment: {result.get('assessment', '')}")
        typer.echo(f"  Decision:   {result.get('decision', '')}")
        risks = result.get("risks", [])
        if risks:
            typer.echo(f"\n  Risks:")
            for r in risks:
                typer.echo(f"    - {r.get('risk', r)}")
                if r.get("mitigation"):
                    typer.echo(f"      Mitigation: {r['mitigation']}")

    elif agent_id == "orchestrator":
        typer.echo(f"\n  Summary: {result.get('summary', '')}")
        workflow = result.get("workflow", [])
        if workflow:
            typer.echo(f"\n  Workflow ({len(workflow)} steps):")
            for step in workflow:
                typer.echo(f"    {step.get('step', '?')}. {step.get('task', '')}")
                if step.get("assigned_to"):
                    typer.echo(f"       → {step['assigned_to']}")

    elif agent_id == "architect":
        typer.echo(f"\n  Analysis: {result.get('analysis', '')}")
        options = result.get("options", [])
        if options:
            typer.echo(f"\n  Options ({len(options)}):")
            for opt in options:
                typer.echo(f"    - {opt.get('name', '')}: {opt.get('description', '')}")
        rec = result.get("recommendation", "")
        if rec:
            typer.echo(f"\n  Recommendation: {rec}")

    elif agent_id == "engineering":
        typer.echo(f"\n  Approach: {result.get('approach', '')}")
        plan = result.get("implementation_plan", [])
        if plan:
            typer.echo(f"\n  Plan:")
            for p in plan:
                typer.echo(f"    - {p}")

    elif agent_id == "qa":
        typer.echo(f"\n  Summary: {result.get('summary', '')}")
        gates = result.get("quality_gates", [])
        if gates:
            typer.echo(f"\n  Quality Gates:")
            for g in gates:
                typer.echo(f"    [{g.get('status', '?')}] {g.get('gate', '')}")
        typer.echo(f"\n  Recommendation: {result.get('recommendation', '')}")

    else:
        # Generic fallback
        output = result.get("output", "")
        if output:
            typer.echo(f"\n  Output:\n{output[:500]}")

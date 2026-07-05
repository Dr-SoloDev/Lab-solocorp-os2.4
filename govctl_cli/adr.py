"""ADR management commands."""
import typer
import tomllib
from pathlib import Path
from typing import Optional
from datetime import datetime

adr_app = typer.Typer(name="adr", help="Manage Architecture Decision Records")
GOV_DIR = Path("gov")


def _adr_dir() -> Path:
    return GOV_DIR / "adr"


def _next_id() -> str:
    existing = list(_adr_dir().glob("ADR-*.toml"))
    nums = [0]
    for p in existing:
        try:
            nums.append(int(p.stem.split("-")[1]))
        except (IndexError, ValueError):
            continue
    return f"ADR-{max(nums) + 1:03d}"


def _read_adr(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


_ADR_TEMPLATE = '''[metadata]
id = "{id}"
title = "{title}"
status = "proposed"
date = "{date}"
version = "1.0.0"
author = "{author}"

[classification]
domain = "{domain}"
impact = "{impact}"
complexity = "{complexity}"
scope = "{scope}"

[body.en]
summary = ""
context = ""
decision = ""
consequences = ""
alternatives = ""

[body.th]
summary = ""
context = ""
decision = ""
consequences = ""
alternatives = ""

[footer]
references = []
tags = []
review_date = "{review_date}"
'''


@adr_app.command()
def new(
    title: str = typer.Argument(..., help="ADR title"),
    author: str = typer.Option("Orchestrator Team", "--author", "-a"),
    domain: str = typer.Option("architecture", "--domain", "-d", help="architecture|engineering|process|governance"),
    impact: str = typer.Option("medium", "--impact", "-i", help="low|medium|high|critical"),
    complexity: str = typer.Option("medium", "--complexity", "-c", help="simple|medium|complex"),
    scope: str = typer.Option("department", "--scope", "-s", help="department|cross-department|organization-wide"),
):
    """Create a new ADR from template."""
    _adr_dir().mkdir(parents=True, exist_ok=True)
    adr_id = _next_id()
    today = datetime.now().strftime("%Y-%m-%d")
    review = datetime.now().replace(year=datetime.now().year + 1).strftime("%Y-%m-%d")

    content = _ADR_TEMPLATE.format(
        id=adr_id,
        title=title,
        date=today,
        author=author,
        domain=domain,
        impact=impact,
        complexity=complexity,
        scope=scope,
        review_date=review,
    )

    path = _adr_dir() / f"{adr_id}.toml"
    path.write_text(content)
    typer.echo(f"✅ Created {adr_id}: {path}")


@adr_app.command("list")
def list_adrs(
    status_filter: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    domain_filter: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """List all ADRs."""
    if not _adr_dir().exists():
        typer.echo("No ADR directory found — run 'govctl init' first")
        raise typer.Exit()

    adrs = sorted(_adr_dir().glob("ADR-*.toml"))
    if not adrs:
        typer.echo("No ADRs found")
        return

    for p in adrs:
        try:
            data = _read_adr(p)
            meta = data.get("metadata", {})
            cls = data.get("classification", {})
            if status_filter and meta.get("status") != status_filter:
                continue
            if domain_filter and cls.get("domain") != domain_filter:
                continue
            en = data.get("body", {}).get("en", {})
            typer.echo(f"  {meta['id']:10s} | {cls.get('impact','?'):8s} | {cls.get('domain','?'):12s} | {meta.get('title','?')}")
        except Exception:
            typer.echo(f"  {p.stem:10s} | ⚠️  parse error")

    typer.echo(f"\nTotal: {len(adrs)} ADRs")


@adr_app.command()
def show(
    adr_id: str = typer.Argument(..., help="ADR ID (e.g. ADR-001)"),
):
    """Show ADR details."""
    path = _adr_dir() / f"{adr_id}.toml"
    if not path.exists():
        typer.echo(f"❌ {adr_id} not found")
        raise typer.Exit(code=1)

    data = _read_adr(path)
    meta = data.get("metadata", {})
    cls = data.get("classification", {})
    en = data.get("body", {}).get("en", {})
    th = data.get("body", {}).get("th", {})

    typer.echo(f"\n{'='*60}")
    typer.echo(f"  {meta.get('id','?')}: {meta.get('title','?')}")
    typer.echo(f"  Status: {meta.get('status','?')} | Date: {meta.get('date','?')}")
    typer.echo(f"  Domain: {cls.get('domain','?')} | Impact: {cls.get('impact','?')} | Complexity: {cls.get('complexity','?')}")
    typer.echo(f"{'='*60}")
    typer.echo(f"\n📝 English Summary: {en.get('summary','')}")
    typer.echo(f"\n📝 ภาษาไทย: {th.get('summary','')}")


@adr_app.command()
def edit(
    adr_id: str = typer.Argument(..., help="ADR ID"),
    field: str = typer.Argument(..., help="Field path e.g. body.en.summary"),
    value: str = typer.Option(None, "--value", "-v", help="New value (use --stdin for multiline)"),
    stdin: bool = typer.Option(False, "--stdin", help="Read value from stdin"),
):
    """Edit an ADR field (simple key=value)."""
    path = _adr_dir() / f"{adr_id}.toml"
    if not path.exists():
        typer.echo(f"❌ {adr_id} not found")
        raise typer.Exit(code=1)

    if stdin:
        import sys
        value = sys.stdin.read().strip()
    elif not value:
        typer.echo("Provide --value or --stdin")
        raise typer.Exit(code=1)

    content = path.read_text()
    parts = field.split(".")
    key = parts[-1]
    old = f'{key} = ""'
    new = f'{key} = """\n{value}\n"""'
    if old in content:
        content = content.replace(old, new, 1)
        path.write_text(content)
        typer.echo(f"✅ Updated {adr_id}: {field}")
    else:
        typer.echo(f"⚠️  Could not find '{old}' in {adr_id}")

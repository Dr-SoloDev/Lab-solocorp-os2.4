"""RFC management commands."""
import typer
from pathlib import Path
from datetime import datetime

rfc_app = typer.Typer(name="rfc", help="Manage Request for Comments")
GOV_DIR = Path("gov")


def _rfc_dir() -> Path:
    return GOV_DIR / "rfc"


def _next_id() -> str:
    existing = sorted(_rfc_dir().glob("RFC-*.toml"))
    nums = [0]
    for p in existing:
        try:
            nums.append(int(p.stem.split("-")[1]))
        except (IndexError, ValueError):
            continue
    return f"RFC-{max(nums) + 1:03d}"


_RFC_TEMPLATE = '''[metadata]
id = "{id}"
title = "{title}"
status = "draft"
author = "{author}"
created = "{date}"
updated = "{date}"

[governance]
threshold_score = {score}
approver = "orchestrator"

[links]
supersedes = []
related_adrs = []
work_items = []

[body.en]
summary = ""
context = ""
proposal = ""
alternatives = ""
consequences = ""

[body.th]
summary = ""
context = ""
proposal = ""
alternatives = ""
consequences = ""
'''


@rfc_app.command()
def new(
    title: str = typer.Argument(..., help="RFC title"),
    author: str = typer.Option("Orchestrator Team", "--author", "-a"),
    score: int = typer.Option(0, "--score", "-s", help="Complexity score 0-3"),
):
    """Create a new RFC."""
    _rfc_dir().mkdir(parents=True, exist_ok=True)
    rfc_id = _next_id()
    today = datetime.now().strftime("%Y-%m-%d")

    content = _RFC_TEMPLATE.format(
        id=rfc_id,
        title=title,
        author=author,
        date=today,
        score=score,
    )

    path = _rfc_dir() / f"{rfc_id}-{title.lower().replace(' ','-')[:40]}.toml"
    path.write_text(content)
    typer.echo(f"✅ Created {rfc_id}: {path}")


@rfc_app.command()
def list():
    """List all RFCs."""
    if not _rfc_dir().exists():
        typer.echo("No RFC directory found")
        return
    rfcs = sorted(_rfc_dir().glob("RFC-*.toml"))
    if not rfcs:
        typer.echo("No RFCs found")
        return
    for p in rfcs:
        import tomllib
        with open(p, "rb") as f:
            data = tomllib.load(f)
        meta = data.get("metadata", {})
        gov = data.get("governance", {})
        score = gov.get("threshold_score", "?")
        typer.echo(f"  {meta.get('id','?'):10s} | score:{score!s:1s} | {meta.get('title','?')}")
    typer.echo(f"\nTotal: {len(rfcs)} RFCs")

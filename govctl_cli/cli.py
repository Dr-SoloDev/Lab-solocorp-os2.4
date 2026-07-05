"""govctl CLI entry point."""
import typer
from pathlib import Path
from . import __version__
from .adr import adr_app
from .rfc import rfc_app
from .guard import guard_app
from .threshold import threshold_app
from .profile_hooks import hook_app
from .validate import validate_app
from .config import config_app
from .ao_cmd import ao_app
from .api_cli import api_app
from .dashboard import cmd_dashboard

app = typer.Typer(
    name="govctl",
    help="SoloCorp OS Governance CLI — RFCs, ADRs, Guards, and Work Items",
)

app.add_typer(adr_app, name="adr", help="Manage Architecture Decision Records")
app.add_typer(rfc_app, name="rfc", help="Manage Request for Comments")
app.add_typer(guard_app, name="guard", help="Manage verification guards")
app.add_typer(threshold_app, name="threshold", help="RFC-001 Complexity Matrix evaluation")
app.add_typer(hook_app, name="hook", help="Profile governance hook management")
app.add_typer(validate_app, name="validate", help="Validate governance artifacts")
app.add_typer(config_app, name="config", help="Manage govctl configuration")

# Optional: bridge module when available
try:
    from .bridge import bridge_app
    app.add_typer(bridge_app, name="bridge", help="Bridge gov/ artifacts to Central Bus")
except ImportError:
    pass

# AO Agent Orchestrator
app.add_typer(ao_app, name="ao", help="Agent Orchestrator — invoke AO agents")

# API Server
app.add_typer(api_app, name="api", help="Start/stop/status FastAPI server")


# ── Dashboard ────────────────────────────────────────────────────────────


@app.command()
def dashboard(
    watch: bool = typer.Option(False, "--watch", "-w", help="Live-updating dashboard"),
    interval: float = typer.Option(5.0, "--interval", "-i", help="Refresh interval in seconds"),
):
    """Terminal-based SoloCorp OS Pipeline Dashboard."""
    cmd_dashboard(watch=watch, interval=interval)


@app.callback()
def main(version: bool = typer.Option(False, "--version", "-v", help="Show version")):
    if version:
        typer.echo(f"govctl v{__version__}")
        raise typer.Exit()


@app.command()
def init(
    dir: Path = typer.Option(Path("gov"), "--dir", "-d", help="Target directory"),
):
    """Initialize governance directory structure."""
    dirs = [dir / "adr", dir / "rfc", dir / "guards", dir / "config"]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()

    config_path = dir / "config.toml"
    if not config_path.exists():
        config_path.write_text("""# govctl configuration
[system]
name = "SoloCorp OS xGov"
version = "0.3.0"

[paths]
adr_dir = "adr"
rfc_dir = "rfc"
guard_dir = "guards"

[governance]
threshold_model = "hybrid"
auto_guard_enforcement = true
""")
    typer.echo(f"✅ Initialized governance structure at {dir.resolve()}")


@app.command()
def status(
    dir: Path = typer.Option(Path("gov"), "--dir", "-d", help="gov directory"),
):
    """Show governance status overview."""
    adr_count = len(list((dir / "adr").glob("*.toml"))) if (dir / "adr").exists() else 0
    rfc_count = len(list((dir / "rfc").glob("*.toml"))) if (dir / "rfc").exists() else 0
    guard_count = len(list((dir / "guards").glob("*.toml"))) if (dir / "guards").exists() else 0

    typer.echo(f"📊 Governance Status ({dir.resolve()})")
    typer.echo(f"   ADRs:   {adr_count}")
    typer.echo(f"   RFCs:   {rfc_count}")
    typer.echo(f"   Guards: {guard_count}")

    if not adr_count and not rfc_count:
        typer.echo("   ⚠️  No artifacts found — run 'govctl init' first")


if __name__ == "__main__":
    app()

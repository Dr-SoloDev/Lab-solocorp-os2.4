"""Configuration commands."""
import typer
from pathlib import Path

config_app = typer.Typer(name="config", help="Manage govctl configuration")
GOV_DIR = Path("gov")


@config_app.command()
def show():
    """Show current configuration."""
    config_path = GOV_DIR / "config.toml"
    if not config_path.exists():
        typer.echo("No config found — run 'govctl init' first")
        return
    typer.echo(config_path.read_text())

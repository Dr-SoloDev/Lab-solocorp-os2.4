"""Validation commands."""
import typer
import tomllib
from pathlib import Path

validate_app = typer.Typer(name="validate", help="Validate governance artifacts")
GOV_DIR = Path("gov")


def _check_toml(path: Path) -> list[str]:
    errors = []
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        if "metadata" not in data:
            errors.append(f"Missing [metadata] section")
        meta = data.get("metadata", {})
        if "id" not in meta:
            errors.append("Missing metadata.id")
        if "body" not in data:
            errors.append("Missing [body] section")
        else:
            for lang in ("en", "th"):
                if lang not in data["body"]:
                    errors.append(f"Missing body.{lang}")
    except tomllib.TOMLDecodeError as e:
        errors.append(f"TOML parse error: {e}")
    except Exception as e:
        errors.append(f"Error: {e}")
    return errors


@validate_app.command()
def adr(
    adr_id: str = typer.Argument(None, help="ADR ID (optional — validate all if omitted)"),
):
    """Validate ADR artifacts."""
    adr_dir = GOV_DIR / "adr"
    if not adr_dir.exists():
        typer.echo("No ADR directory found")
        raise typer.Exit(code=1)

    if adr_id:
        targets = [adr_dir / f"{adr_id}.toml"]
    else:
        targets = sorted(adr_dir.glob("ADR-*.toml"))

    if not targets:
        typer.echo("No ADRs found to validate")
        return

    passed = 0
    failed = 0
    for path in targets:
        if not path.exists():
            typer.echo(f"  ❌ {path.name} — NOT FOUND")
            failed += 1
            continue
        errors = _check_toml(path)
        tp = path.stem
        if errors:
            typer.echo(f"  ❌ {tp}")
            for e in errors:
                typer.echo(f"      - {e}")
            failed += 1
        else:
            typer.echo(f"  ✅ {tp}")
            passed += 1

    typer.echo(f"\n📊 Result: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1

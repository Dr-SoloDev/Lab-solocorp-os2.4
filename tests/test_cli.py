"""Tests for govctl_cli/cli.py — init and status commands."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path

from typer.testing import CliRunner

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from govctl_cli.cli import app

runner = CliRunner()


@contextmanager
def _working_dir(path: Path):
    """Context manager that temporarily changes to *path*."""
    old = os.getcwd()
    os.chdir(path)
    try:
        yield path
    finally:
        os.chdir(old)


class TestInit:
    """Tests for the ``init`` command."""

    def test_init_default_dir(self, tmp_path: Path) -> None:
        """Default ``--dir=gov`` creates the standard governance structure."""
        with _working_dir(tmp_path) as td:
            result = runner.invoke(app, ["init"])
            assert result.exit_code == 0
            assert "Initialized governance structure" in result.stdout

            gov = Path(td) / "gov"
            assert (gov / "adr" / ".gitkeep").exists()
            assert (gov / "rfc" / ".gitkeep").exists()
            assert (gov / "guards" / ".gitkeep").exists()
            assert (gov / "config" / ".gitkeep").exists()
            assert (gov / "config.toml").exists()

    def test_init_custom_dir(self, tmp_path: Path) -> None:
        """``--dir`` creates the structure at a user-specified location."""
        with _working_dir(tmp_path) as td:
            result = runner.invoke(app, ["init", "--dir", "custom-gov"])
            assert result.exit_code == 0

            gov = Path(td) / "custom-gov"
            assert (gov / "adr" / ".gitkeep").exists()
            assert (gov / "rfc" / ".gitkeep").exists()
            assert (gov / "guards" / ".gitkeep").exists()
            assert (gov / "config" / ".gitkeep").exists()
            assert (gov / "config.toml").exists()

            # The default 'gov' directory must not be created when --dir is used
            assert not (Path(td) / "gov").exists()


class TestStatus:
    """Tests for the ``status`` command."""

    def test_status_after_init(self, tmp_path: Path) -> None:
        """status after init displays the governance overview header and labels."""
        with _working_dir(tmp_path):
            runner.invoke(app, ["init"])
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "Governance Status" in result.stdout
            assert "ADRs:" in result.stdout
            assert "RFCs:" in result.stdout
            assert "Guards:" in result.stdout

    def test_status_no_artifacts(self, tmp_path: Path) -> None:
        """status without prior init warns the user."""
        with _working_dir(tmp_path):
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "No artifacts found" in result.stdout
            assert "run 'govctl init' first" in result.stdout


def test_dashboard_no_metrics_no_crash(tmp_path, monkeypatch):
    """dashboard must not traceback when no metrics exist."""
    import pytest
    from govctl_cli.dashboard.dashboard import run_dashboard
    monkeypatch.chdir(tmp_path)
    try:
        run_dashboard(watch=False)
    except SystemExit:
        pass  # acceptable
    except Exception as exc:
        pytest.fail(f"run_dashboard raised unexpectedly: {type(exc).__name__}: {exc}")

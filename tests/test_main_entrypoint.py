"""
Unit tests for govctl_cli/__main__.py (ENG-05).

Verifies that `python -m govctl_cli` can be invoked as a CLI entry point
without crashing at import time.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent


def test_module_entry_point_shows_help():
    """python -m govctl_cli --help exits 0 and prints usage text."""
    result = subprocess.run(
        [sys.executable, "-m", "govctl_cli", "--help"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    # Typer/Click prints help and exits 0
    assert result.returncode == 0, (
        f"Expected exit 0 from --help, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert "usage" in combined or "govctl" in combined, (
        f"Expected usage text in output, got: {combined!r}"
    )


def test_module_entry_point_no_args_does_not_crash():
    """python -m govctl_cli (no args) exits without an unhandled exception."""
    result = subprocess.run(
        [sys.executable, "-m", "govctl_cli"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    # Typer exits 0 (prints help) or 2 (missing command) — both are valid.
    # What we never want is exit 1 with a Python traceback.
    assert "Traceback" not in result.stderr, (
        f"Unexpected traceback:\n{result.stderr}"
    )
    assert result.returncode in (0, 2), (
        f"Unexpected exit code {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_cli_runner_invoke():
    """Use Typer CliRunner to invoke govctl_cli app directly."""
    from typer.testing import CliRunner
    from govctl_cli.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert result.output  # some help text was printed

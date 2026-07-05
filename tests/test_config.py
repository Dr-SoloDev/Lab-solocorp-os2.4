"""Tests for govctl_cli/config.py — config show command."""
from __future__ import annotations

import sys
from pathlib import Path

import govctl_cli.config as config_mod
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from govctl_cli.cli import app

runner = CliRunner()


class TestConfigShow:
    """govctl config show — display config.toml."""

    def test_no_config_file(self, tmp_path, monkeypatch):
        """When gov/config.toml does not exist, print 'No config found'."""
        monkeypatch.setattr(config_mod, "GOV_DIR", tmp_path)
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "No config found" in result.stdout

    def test_with_config_file(self, tmp_path, monkeypatch):
        """When gov/config.toml exists, print its contents."""
        monkeypatch.setattr(config_mod, "GOV_DIR", tmp_path)
        config_content = (
            '[system]\n'
            'name = "SoloCorp OS xGov"\n'
            'version = "0.3.0"\n'
        )
        (tmp_path / "config.toml").write_text(config_content)
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "SoloCorp OS xGov" in result.stdout
        assert "0.3.0" in result.stdout


# ── ENG-13: structural checks on gov/config.toml ──────────────────────────

import tomllib


def test_config_has_api_section():
    data = tomllib.loads(Path("gov/config.toml").read_bytes().decode())
    assert "api" in data, "gov/config.toml must have [api] section for middleware config"


def test_api_section_has_require_auth():
    data = tomllib.loads(Path("gov/config.toml").read_bytes().decode())
    assert "require_auth" in data.get("api", {}), "[api] section must have require_auth key"

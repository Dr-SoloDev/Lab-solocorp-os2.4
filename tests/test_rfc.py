"""Tests for RFC management commands and utilities."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typer.testing import CliRunner

from govctl_cli.cli import app
import govctl_cli.rfc as rfc_mod


class TestRfcUtils:
    """Pure-function tests for _rfc_dir and _next_id."""

    def test_rfc_dir_returns_gov_dir_plus_rfc(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rfc_mod, "GOV_DIR", tmp_path)
        assert rfc_mod._rfc_dir() == tmp_path / "rfc"

    def test_next_id_empty_dir(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rfc_mod, "GOV_DIR", tmp_path)
        assert rfc_mod._next_id() == "RFC-001"

    def test_next_id_with_existing_rfc_001(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rfc_mod, "GOV_DIR", tmp_path)
        rfc_dir = rfc_mod._rfc_dir()
        rfc_dir.mkdir(parents=True)
        (rfc_dir / "RFC-001-test.toml").touch()
        assert rfc_mod._next_id() == "RFC-002"


class TestRfcCli:
    """CLI tests for the rfc command group."""

    runner = CliRunner()

    def test_new_creates_rfc_001(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rfc_mod, "GOV_DIR", tmp_path)
        result = self.runner.invoke(app, ["rfc", "new", "Test Title"])
        assert result.exit_code == 0
        assert "RFC-001" in result.stdout
        rfc_file = tmp_path / "rfc" / "RFC-001-test-title.toml"
        assert rfc_file.exists()
        content = rfc_file.read_text()
        assert 'id = "RFC-001"' in content
        assert 'title = "Test Title"' in content
        assert 'author = "Orchestrator Team"' in content
        assert "threshold_score = 0" in content

    def test_new_with_custom_params(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rfc_mod, "GOV_DIR", tmp_path)
        result = self.runner.invoke(
            app, ["rfc", "new", "Foo", "--author", "Me", "--score", "2"]
        )
        assert result.exit_code == 0
        assert "RFC-001" in result.stdout
        rfc_file = tmp_path / "rfc" / "RFC-001-foo.toml"
        assert rfc_file.exists()
        content = rfc_file.read_text()
        assert 'id = "RFC-001"' in content
        assert 'title = "Foo"' in content
        assert 'author = "Me"' in content
        assert "threshold_score = 2" in content

    def test_list_no_directory(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rfc_mod, "GOV_DIR", tmp_path)
        result = self.runner.invoke(app, ["rfc", "list"])
        assert result.exit_code == 0
        assert "No RFC directory found" in result.stdout

    def test_list_empty_directory(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rfc_mod, "GOV_DIR", tmp_path)
        rfc_mod._rfc_dir().mkdir(parents=True)
        result = self.runner.invoke(app, ["rfc", "list"])
        assert result.exit_code == 0
        assert "No RFCs found" in result.stdout

    def test_list_returns_rfcs(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rfc_mod, "GOV_DIR", tmp_path)
        self.runner.invoke(app, ["rfc", "new", "First RFC"])
        self.runner.invoke(app, ["rfc", "new", "Second RFC"])
        result = self.runner.invoke(app, ["rfc", "list"])
        assert result.exit_code == 0
        assert "RFC-001" in result.stdout
        assert "RFC-002" in result.stdout
        assert "First RFC" in result.stdout
        assert "Second RFC" in result.stdout
        assert "Total: 2 RFCs" in result.stdout

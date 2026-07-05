"""Tests for govctl_cli/validate.py — _check_toml and validate adr CLI."""
from __future__ import annotations

import sys
from pathlib import Path

import govctl_cli.validate as val_mod
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from govctl_cli.cli import app

runner = CliRunner()


# ── _check_toml (pure function) ──────────────────────────────────────────


class TestCheckToml:
    """Unit tests for _check_toml — TOML structure validation."""

    def test_valid_toml(self, tmp_path: Path) -> None:
        """Valid TOML with metadata + body.en + body.th returns empty list."""
        adr = tmp_path / "ADR-001.toml"
        adr.write_text("""\
[metadata]
id = "ADR-001"

[body]
en = "English summary"
th = "สรุปภาษาไทย"
""")
        assert val_mod._check_toml(adr) == []

    def test_missing_metadata_section(self, tmp_path: Path) -> None:
        """Missing [metadata] section returns error."""
        adr = tmp_path / "ADR-001.toml"
        adr.write_text("""\
[body]
en = "English summary"
th = "สรุปภาษาไทย"
""")
        errors = val_mod._check_toml(adr)
        assert "Missing [metadata] section" in errors

    def test_missing_metadata_id(self, tmp_path: Path) -> None:
        """[metadata] present but missing id returns error."""
        adr = tmp_path / "ADR-001.toml"
        adr.write_text("""\
[metadata]
title = "Test"

[body]
en = "English summary"
th = "สรุปภาษาไทย"
""")
        errors = val_mod._check_toml(adr)
        assert "Missing metadata.id" in errors

    def test_missing_body_section(self, tmp_path: Path) -> None:
        """Missing [body] section returns error."""
        adr = tmp_path / "ADR-001.toml"
        adr.write_text("""\
[metadata]
id = "ADR-001"
""")
        errors = val_mod._check_toml(adr)
        assert "Missing [body] section" in errors

    def test_missing_body_en(self, tmp_path: Path) -> None:
        """[body] present but missing body.en returns error."""
        adr = tmp_path / "ADR-001.toml"
        adr.write_text("""\
[metadata]
id = "ADR-001"

[body]
th = "สรุปภาษาไทย"
""")
        errors = val_mod._check_toml(adr)
        assert "Missing body.en" in errors

    def test_missing_body_th(self, tmp_path: Path) -> None:
        """[body] present but missing body.th returns error."""
        adr = tmp_path / "ADR-001.toml"
        adr.write_text("""\
[metadata]
id = "ADR-001"

[body]
en = "English summary"
""")
        errors = val_mod._check_toml(adr)
        assert "Missing body.th" in errors

    def test_invalid_toml(self, tmp_path: Path) -> None:
        """Completely invalid TOML returns TOML parse error."""
        adr = tmp_path / "ADR-001.toml"
        adr.write_text("this is not valid toml {{{")
        errors = val_mod._check_toml(adr)
        assert any("TOML parse error" in e for e in errors)


# ── CLI: validate adr ────────────────────────────────────────────────────


class TestValidateAdrCli:
    """CLI tests for `govctl validate adr` using CliRunner."""

    def test_no_adr_directory(self, monkeypatch, tmp_path: Path) -> None:
        """When no gov/adr directory exists, print 'No ADR directory found' and exit non-zero."""
        monkeypatch.setattr(val_mod, "GOV_DIR", tmp_path)
        result = runner.invoke(app, ["validate", "adr"])
        assert result.exit_code == 1
        assert "No ADR directory found" in result.stdout

    def test_empty_adr_directory(self, monkeypatch, tmp_path: Path) -> None:
        """When gov/adr exists but is empty, print 'No ADRs found'."""
        (tmp_path / "adr").mkdir(parents=True)
        monkeypatch.setattr(val_mod, "GOV_DIR", tmp_path)
        result = runner.invoke(app, ["validate", "adr"])
        assert "No ADRs found to validate" in result.stdout

    def test_valid_adr_by_id(self, monkeypatch, tmp_path: Path) -> None:
        """When ADR-001.toml exists and is valid, print ✅ ADR-001."""
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "ADR-001.toml").write_text("""\
[metadata]
id = "ADR-001"

[body]
en = "English summary"
th = "สรุปภาษาไทย"
""")
        monkeypatch.setattr(val_mod, "GOV_DIR", tmp_path)
        result = runner.invoke(app, ["validate", "adr", "ADR-001"])
        assert result.exit_code == 0
        assert "✅ ADR-001" in result.stdout

    def test_adr_not_found(self, monkeypatch, tmp_path: Path) -> None:
        """When ADR-999.toml does not exist, print NOT FOUND."""
        (tmp_path / "adr").mkdir(parents=True)
        monkeypatch.setattr(val_mod, "GOV_DIR", tmp_path)
        result = runner.invoke(app, ["validate", "adr", "ADR-999"])
        assert "NOT FOUND" in result.stdout

    def test_adr_with_errors(self, monkeypatch, tmp_path: Path) -> None:
        """When ADR-001.toml exists but has validation errors, print ❌ with error details."""
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "ADR-001.toml").write_text("""\
[metadata]
id = "ADR-001"
""")
        monkeypatch.setattr(val_mod, "GOV_DIR", tmp_path)
        result = runner.invoke(app, ["validate", "adr", "ADR-001"])
        assert "❌ ADR-001" in result.stdout
        assert "Missing [body] section" in result.stdout

    def test_validate_all_adrs(self, monkeypatch, tmp_path: Path) -> None:
        """Without an ADR ID, validate every ADR-*.toml in the directory."""
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "ADR-001.toml").write_text("""\
[metadata]
id = "ADR-001"

[body]
en = "English summary"
th = "สรุปภาษาไทย"
""")
        (adr_dir / "ADR-002.toml").write_text("""\
[metadata]
id = "ADR-002"

[body]
en = "English summary"
th = "สรุปภาษาไทย"
""")
        monkeypatch.setattr(val_mod, "GOV_DIR", tmp_path)
        result = runner.invoke(app, ["validate", "adr"])
        assert result.exit_code == 0
        assert "✅ ADR-001" in result.stdout
        assert "✅ ADR-002" in result.stdout
        assert "2 passed" in result.stdout

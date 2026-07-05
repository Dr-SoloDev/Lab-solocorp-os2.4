"""Tests for govctl_cli/adr.py — ADR lifecycle: new, list, show, edit."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import govctl_cli.adr as adr_mod
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from govctl_cli.cli import app  # noqa: E402

runner = CliRunner()


# ── _next_id() ──────────────────────────────────────────────────────────────


class TestNextId:
    """ADR-XXX sequential ID generation."""

    # NOTE: _next_id() calls built-in list() to collect glob results.
    #       Govctl's own CLI list command was renamed to list_adrs to avoid
    #       shadowing that built-in.

    def test_empty_dir_returns_001(self, tmp_path, monkeypatch):
        """No ADR files at all → _next_id() == 'ADR-001'."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        assert adr_mod._next_id() == "ADR-001"

    def test_with_existing_001_returns_002(self, tmp_path, monkeypatch):
        """ADR-001.toml exists → _next_id() == 'ADR-002'."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        (tmp_path / "adr").mkdir(parents=True)
        (tmp_path / "adr" / "ADR-001.toml").write_text("")
        assert adr_mod._next_id() == "ADR-002"

    def test_with_gap_returns_next_sequential(self, tmp_path, monkeypatch):
        """ADR-001 + ADR-003 → _next_id() == 'ADR-004' (max + 1, not count)."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        (tmp_path / "adr").mkdir(parents=True)
        (tmp_path / "adr" / "ADR-001.toml").write_text("")
        (tmp_path / "adr" / "ADR-003.toml").write_text("")
        assert adr_mod._next_id() == "ADR-004"

    def test_malformed_files_ignored(self, tmp_path, monkeypatch):
        """README.md (no ADR- prefix) is not matched by glob → returns ADR-001."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        (tmp_path / "adr").mkdir(parents=True)
        (tmp_path / "adr" / "README.md").write_text("# notes")
        assert adr_mod._next_id() == "ADR-001"

    def test_invalid_number_in_name_skipped(self, tmp_path, monkeypatch):
        """ADR-abc.toml has non-numeric suffix → skipped → ADR-001."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        (tmp_path / "adr").mkdir(parents=True)
        (tmp_path / "adr" / "ADR-abc.toml").write_text("")
        assert adr_mod._next_id() == "ADR-001"


# ── _read_adr() ─────────────────────────────────────────────────────────────


class TestReadAdr:
    """Reading a valid TOML file back as a Python dict."""

    def test_returns_dict(self, tmp_path):
        """Parsing a minimal TOML file produces the expected dict."""
        p = tmp_path / "ADR-001.toml"
        p.write_text('title = "Hello"\ncount = 42\n')
        result = adr_mod._read_adr(p)
        assert result == {"title": "Hello", "count": 42}

    def test_missing_file(self, tmp_path):
        """Reading a non-existent file raises FileNotFoundError."""
        p = tmp_path / "no-such-file.toml"
        with pytest.raises(FileNotFoundError):
            adr_mod._read_adr(p)


# ── CLI: adr new ────────────────────────────────────────────────────────────


class TestCliNew:
    """govctl adr new — create ADR files from template."""

    def test_creates_adr_001(self, tmp_path, monkeypatch):
        """Basic invocation creates ADR-001.toml with template fields."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        result = runner.invoke(app, ["adr", "new", "Test Title"])
        assert result.exit_code == 0
        adr_path = tmp_path / "adr" / "ADR-001.toml"
        assert adr_path.exists()
        content = adr_path.read_text()
        assert 'title = "Test Title"' in content
        assert 'id = "ADR-001"' in content
        assert 'status = "proposed"' in content

    def test_custom_params(self, tmp_path, monkeypatch):
        """All custom --author / --domain / --impact / --complexity / --scope
        flags are written into the generated template."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        result = runner.invoke(app, [
            "adr", "new", "Foo",
            "--author", "Me",
            "--domain", "engineering",
            "--impact", "high",
            "--complexity", "complex",
            "--scope", "organization-wide",
        ])
        assert result.exit_code == 0
        adr_path = tmp_path / "adr" / "ADR-001.toml"
        assert adr_path.exists()
        content = adr_path.read_text()
        assert 'author = "Me"' in content
        assert 'domain = "engineering"' in content
        assert 'impact = "high"' in content
        assert 'complexity = "complex"' in content
        assert 'scope = "organization-wide"' in content

    def test_creates_multiple_adrs_increments_id(self, tmp_path, monkeypatch):
        """Two sequential `adr new` calls produce ADR-001 and ADR-002."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        r1 = runner.invoke(app, ["adr", "new", "First"])
        assert r1.exit_code == 0
        assert (tmp_path / "adr" / "ADR-001.toml").exists()

        r2 = runner.invoke(app, ["adr", "new", "Second"])
        assert r2.exit_code == 0
        assert (tmp_path / "adr" / "ADR-002.toml").exists()


# ── CLI: adr list ────────────────────────────────────────────────────────────


class TestCliList:
    """govctl adr list — list / filter ADRs."""

    def test_no_adr_directory(self, tmp_path, monkeypatch):
        """When gov/adr does not exist at all, print guidance message."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        result = runner.invoke(app, ["adr", "list"])
        assert result.exit_code == 0
        assert "No ADR directory found" in result.stdout

    def test_empty_adr_directory(self, tmp_path, monkeypatch):
        """When gov/adr exists but holds no ADR-*.toml files, print 'No ADRs found'."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        (tmp_path / "adr").mkdir(parents=True)
        result = runner.invoke(app, ["adr", "list"])
        assert result.exit_code == 0
        assert "No ADRs found" in result.stdout

    def test_lists_single_adr(self, tmp_path, monkeypatch):
        """Create one ADR and verify it appears in list output."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        runner.invoke(app, ["adr", "new", "My ADR"])
        result = runner.invoke(app, ["adr", "list"])
        assert result.exit_code == 0
        assert "ADR-001" in result.stdout
        assert "Total: 1 ADRs" in result.stdout

    def test_lists_multiple_adrs(self, tmp_path, monkeypatch):
        """Two ADRs both appear in list output with correct total."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        runner.invoke(app, ["adr", "new", "One"])
        runner.invoke(app, ["adr", "new", "Two"])
        result = runner.invoke(app, ["adr", "list"])
        assert result.exit_code == 0
        assert "ADR-001" in result.stdout
        assert "ADR-002" in result.stdout
        assert "Total: 2 ADRs" in result.stdout

    def test_filter_by_status_match(self, tmp_path, monkeypatch):
        """--status proposed shows matching ADR."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        runner.invoke(app, ["adr", "new", "Match"])
        result = runner.invoke(app, ["adr", "list", "--status", "proposed"])
        assert result.exit_code == 0
        assert "ADR-001" in result.stdout

    def test_filter_by_status_no_match(self, tmp_path, monkeypatch):
        """--status approved filters out the proposed ADR (still shows total)."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        runner.invoke(app, ["adr", "new", "Only Proposed"])
        result = runner.invoke(app, ["adr", "list", "--status", "approved"])
        assert result.exit_code == 0
        assert "Total: 1 ADRs" in result.stdout
        assert "ADR-001" not in result.stdout

    def test_filter_by_domain_match(self, tmp_path, monkeypatch):
        """--domain engineering shows ADRs in that domain."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        runner.invoke(app, ["adr", "new", "For Engineering",
                            "--domain", "engineering"])
        result = runner.invoke(app, ["adr", "list", "--domain", "engineering"])
        assert result.exit_code == 0
        assert "ADR-001" in result.stdout

    def test_filter_by_domain_no_match(self, tmp_path, monkeypatch):
        """--domain finance filters out the engineering ADR."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        runner.invoke(app, ["adr", "new", "For Engineering",
                            "--domain", "engineering"])
        result = runner.invoke(app, ["adr", "list", "--domain", "finance"])
        assert result.exit_code == 0
        assert "Total: 1 ADRs" in result.stdout
        assert "ADR-001" not in result.stdout

    def test_filter_status_and_domain(self, tmp_path, monkeypatch):
        """Combined --status + --domain filter narrows results."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        runner.invoke(app, ["adr", "new", "Eng Proposal",
                            "--domain", "engineering"])
        runner.invoke(app, ["adr", "new", "Gov Decision",
                            "--domain", "governance"])
        result = runner.invoke(app, [
            "adr", "list", "--status", "proposed", "--domain", "governance",
        ])
        assert result.exit_code == 0
        assert "ADR-002" in result.stdout  # governance one matches
        assert "ADR-001" not in result.stdout  # engineering filtered out
        assert "Total: 2 ADRs" in result.stdout


# ── CLI: adr show ────────────────────────────────────────────────────────────


class TestCliShow:
    """govctl adr show — display a single ADR in full."""

    def test_show_existing_adr(self, tmp_path, monkeypatch):
        """show ADR-001 prints its title, status, and summary sections."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        runner.invoke(app, ["adr", "new", "Display Test"])
        result = runner.invoke(app, ["adr", "show", "ADR-001"])
        assert result.exit_code == 0
        assert "ADR-001" in result.stdout
        assert "Display Test" in result.stdout
        assert "proposed" in result.stdout
        assert "English Summary" in result.stdout
        assert "ภาษาไทย" in result.stdout

    def test_show_nonexistent(self, tmp_path, monkeypatch):
        """Show a non-existent ADR prints 'not found' and exits with code 1."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        result = runner.invoke(app, ["adr", "show", "NONEXISTENT"])
        assert result.exit_code == 1
        assert "not found" in result.stdout


# ── CLI: adr edit ────────────────────────────────────────────────────────────


class TestCliEdit:
    """govctl adr edit — modify a field in an existing ADR."""

    def test_edit_field(self, tmp_path, monkeypatch):
        """--value replaces an empty-string field in the TOML."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        runner.invoke(app, ["adr", "new", "Editable ADR"])
        result = runner.invoke(app, [
            "adr", "edit", "ADR-001",
            "body.en.summary",
            "--value", "new summary",
        ])
        assert result.exit_code == 0
        assert "Updated ADR-001: body.en.summary" in result.stdout
        content = (tmp_path / "adr" / "ADR-001.toml").read_text()
        assert "new summary" in content

    def test_edit_multiline_via_stdin(self, tmp_path, monkeypatch):
        """--stdin reads multiline value from stdin."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        runner.invoke(app, ["adr", "new", "Multiline ADR"])
        result = runner.invoke(app, [
            "adr", "edit", "ADR-001",
            "body.en.context",
            "--stdin",
        ], input="line1\nline2\nline3")
        assert result.exit_code == 0
        content = (tmp_path / "adr" / "ADR-001.toml").read_text()
        assert "line1" in content
        assert "line2" in content
        assert "line3" in content

    def test_edit_nonexistent(self, tmp_path, monkeypatch):
        """Editing a non-existent ADR prints error and exits with code 1."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        result = runner.invoke(app, [
            "adr", "edit", "NONEXISTENT",
            "body.en.summary",
            "--value", "x",
        ])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_edit_missing_value(self, tmp_path, monkeypatch):
        """No --value and no --stdin prints an error message."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        runner.invoke(app, ["adr", "new", "No Value ADR"])
        result = runner.invoke(app, [
            "adr", "edit", "ADR-001",
            "body.en.summary",
        ])
        assert result.exit_code == 1
        assert "Provide --value or --stdin" in result.stdout

    def test_edit_unknown_field_shows_warning(self, tmp_path, monkeypatch):
        """Editing a non-existent template field produces a warning, not a crash."""
        monkeypatch.setattr(adr_mod, "GOV_DIR", tmp_path)
        runner.invoke(app, ["adr", "new", "Unknown Field ADR"])
        result = runner.invoke(app, [
            "adr", "edit", "ADR-001",
            "body.en.nonexistent",
            "--value", "whatever",
        ])
        assert result.exit_code == 0
        assert "Could not find" in result.stdout


# ── CLI: adr — help (app-level) ─────────────────────────────────────────────


class TestCliApp:
    """govctl adr — top-level app behaviour."""

    def test_adr_help(self):
        """--help lists available commands: new, list, show, edit."""
        result = runner.invoke(app, ["adr", "--help"])
        assert result.exit_code == 0
        assert "new" in result.stdout
        assert "list" in result.stdout
        assert "show" in result.stdout
        assert "edit" in result.stdout

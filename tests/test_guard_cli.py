"""CLI integration tests for guard commands via CliRunner."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from typer.testing import CliRunner

import govctl_cli.guard as guard_mod


# ── Helpers ──────────────────────────────────────────────────────────────


GUARD_SPEC_TOML = """\
[metadata]
id = "default"
title = "Default Guard Profile"
status = "active"
version = "1.0.0"
applies_to = ["*"]

[execution]
order = ["GUARD-001", "GUARD-002", "GUARD-003", "GUARD-004", "GUARD-005", "GUARD-006", "GUARD-007", "GUARD-008", "GUARD-009"]

[[guards]]
id = "GUARD-001"
name = "Metadata Completeness"
type = "automated"
severity = "blocking"

[[guards]]
id = "GUARD-002"
name = "Classification Schema"
type = "automated"
severity = "blocking"

[[guards]]
id = "GUARD-003"
name = "Bilingual Completeness"
type = "automated"
severity = "blocking"

[[guards]]
id = "GUARD-004"
name = "Decision Statement"
type = "automated"
severity = "blocking"

[[guards]]
id = "GUARD-005"
name = "Review Date"
type = "automated"
severity = "warning"

[[guards]]
id = "GUARD-006"
name = "Cross-Reference Integrity"
type = "automated"
severity = "warning"

[[guards]]
id = "GUARD-007"
name = "Stakeholder Sign-off"
type = "manual"
severity = "blocking"

[[guards]]
id = "GUARD-008"
name = "Cross-Dept Notification"
type = "manual"
severity = "blocking"

[[guards]]
id = "GUARD-009"
name = "Reality Checker"
type = "manual"
severity = "blocking"
"""


ADR_TOML = """\
[metadata]
id = "ADR-099"
title = "Test ADR"
status = "proposed"
date = "2026-07-05"
author = "Tester"

[classification]
domain = "architecture"
impact = "medium"
complexity = "low"
scope = "department"

[body.en]
summary = "Test"
context = "Test"
decision = "Test"
consequences = "Test"
alternatives = ""

[body.th]
summary = "ทดสอบ"
context = "ทดสอบ"
decision = "ทดสอบ"
consequences = "ทดสอบ"
alternatives = ""

[footer]
references = []
tags = []
review_date = "2027-07-05"
"""


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def app():
    from govctl_cli.cli import app
    return app


@pytest.fixture
def guard_env(tmp_path, runner, app):
    """Set up GOV_DIR → tmp_path, create guard spec and ADR artifact.

    Yields (tmp_path, adr_path) for tests that need the paths.
    """
    monkeypatch = pytest.MonkeyPatch()

    monkeypatch.setattr(guard_mod, "GOV_DIR", tmp_path)
    monkeypatch.setattr(guard_mod, "AUDIT_DIR", tmp_path / "audit")

    # Create guard spec
    spec_dir = tmp_path / "guards"
    spec_dir.mkdir(parents=True)
    (spec_dir / "default.toml").write_text(GUARD_SPEC_TOML)

    # Create ADR artifact
    adr_path = tmp_path / "ADR-099.toml"
    adr_path.write_text(ADR_TOML)

    yield tmp_path, adr_path

    monkeypatch.undo()


@pytest.fixture
def invalid_adr_path(tmp_path):
    """Create an ADR with invalid fields so GUARD-001 fails."""
    adr_path = tmp_path / "ADR-INVALID.toml"
    adr_path.write_text("""\
[metadata]
id = ""
title = ""
status = "bogus"
date = "not-a-date"
author = ""

[classification]
domain = "unknown"
impact = "extreme"
complexity = "extreme"
scope = ""

[body.en]
summary = ""
context = ""
decision = ""
consequences = ""

[body.th]
summary = ""
context = ""
decision = ""
consequences = ""

[footer]
references = []
tags = []
review_date = ""
""")
    return adr_path


# ── guard list ───────────────────────────────────────────────────────────


class TestGuardList:
    """Tests for ``guard list``."""

    def test_list_guards(self, runner, app, guard_env):
        """When guards dir exists with default.toml → lists guards."""
        result = runner.invoke(app, ["guard", "list"])
        assert result.exit_code == 0
        assert "Metadata Completeness" in result.stdout
        assert "Stakeholder Sign-off" in result.stdout
        assert "GUARD-001" in result.stdout
        assert "GUARD-007" in result.stdout

    def test_list_no_guards_dir(self, runner, app):
        """When guards dir does NOT exist → 'No guards directory found'."""
        # Use a fresh isolated tmp — no guard env setup so GOV_DIR is relative
        # and won't exist in the fs.
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["guard", "list"])
            assert result.exit_code == 0
            assert "No guards directory found" in result.stdout

    def test_list_empty_guards_dir(self, runner, app):
        """When guards dir exists but empty → 'No guard profiles found'."""
        with runner.isolated_filesystem():
            # Create an empty guards directory
            Path("gov/guards").mkdir(parents=True)
            result = runner.invoke(app, ["guard", "list"])
            assert result.exit_code == 0
            assert "No guard profiles found" in result.stdout


# ── guard run ────────────────────────────────────────────────────────────


class TestGuardRun:
    """Tests for ``guard run``."""

    def test_run_without_target(self, runner, app, guard_env):
        """Without --target → '❌ --target/-t is required'."""
        result = runner.invoke(app, ["guard", "run"])
        assert result.exit_code == 1
        assert "❌" in result.stdout
        assert "target" in result.stdout.lower()

    def test_run_with_target(self, runner, app, guard_env):
        """With --target pointing to a valid ADR TOML and --profile default →
        runs all guards (does not crash).
        """
        _tmp_path, adr_path = guard_env
        result = runner.invoke(app, ["guard", "run", "--target", str(adr_path)])
        assert result.exit_code == 0
        # Should have run through the execution order
        assert "Guard Profile:" in result.stdout
        assert "Target:" in result.stdout
        assert "Results:" in result.stdout
        # Automated guards ran
        assert "GUARD-001" in result.stdout
        assert "GUARD-002" in result.stdout
        # Manual guards show pending
        assert "Manual guard" in result.stdout
        assert "requires human approval" in result.stdout


# ── guard check ──────────────────────────────────────────────────────────


class TestGuardCheck:
    """Tests for ``guard check GUARD-001``."""

    def test_check_without_target(self, runner, app, guard_env):
        """Without --target → '❌ --target/-t is required'."""
        result = runner.invoke(app, ["guard", "check", "GUARD-001"])
        assert result.exit_code == 1
        assert "❌" in result.stdout
        assert "target" in result.stdout.lower()

    def test_check_invalid_guard_id(self, runner, app, guard_env):
        """With invalid guard ID → 'not found in profile'."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app, ["guard", "check", "GUARD-999", "--target", str(adr_path)]
        )
        assert result.exit_code == 1
        assert "not found in profile" in result.stdout

    def test_check_valid_guard_and_target(self, runner, app, guard_env):
        """With valid guard and target → runs single check successfully."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app, ["guard", "check", "GUARD-001", "--target", str(adr_path)]
        )
        assert result.exit_code == 0  # ADR-099 has all required fields
        assert "GUARD-001" in result.stdout
        assert "Metadata Completeness" in result.stdout


# ── guard approve ────────────────────────────────────────────────────────


class TestGuardApprove:
    """Tests for ``guard approve GUARD-007 --target <path> --approver <name>``."""

    def test_approve_manual_guard(self, runner, app, guard_env):
        """Approves a manual guard → creates approval log file."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app,
            [
                "guard",
                "approve",
                "GUARD-007",
                "--target",
                str(adr_path),
                "--approver",
                "Tester",
            ],
        )
        assert result.exit_code == 0
        assert "APPROVED by Tester" in result.stdout

        # Verify the approval log was written
        log_file = (
            guard_mod.AUDIT_DIR
            / "approval-log"
            / f"GUARD-007_{adr_path.stem}.json"
        )
        assert log_file.exists()
        record = json.loads(log_file.read_text())
        assert record["guard_id"] == "GUARD-007"
        assert record["approver"] == "Tester"
        assert record["status"] == "approved"

    def test_approve_invalid_guard_id(self, runner, app, guard_env):
        """With invalid guard ID → 'not found in profile'."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app,
            [
                "guard",
                "approve",
                "GUARD-999",
                "--target",
                str(adr_path),
                "--approver",
                "Tester",
            ],
        )
        assert result.exit_code == 1
        assert "not found in profile" in result.stdout

    def test_approve_non_manual_guard(self, runner, app, guard_env):
        """With non-manual guard → 'is not a manual guard'."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app,
            [
                "guard",
                "approve",
                "GUARD-001",
                "--target",
                str(adr_path),
                "--approver",
                "Tester",
            ],
        )
        assert result.exit_code == 1
        assert "not a manual guard" in result.stdout

    def test_approve_without_approver(self, runner, app, guard_env):
        """Without --approver → '❌ --approver/-a is required'."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app,
            ["guard", "approve", "GUARD-007", "--target", str(adr_path)],
        )
        assert result.exit_code == 1
        assert "❌" in result.stdout
        assert "approver" in result.stdout.lower()


# ── guard reject ─────────────────────────────────────────────────────────


class TestGuardReject:
    """Tests for ``guard reject GUARD-007 --target <path> --approver <name> --reason <r>``."""

    def test_reject_manual_guard(self, runner, app, guard_env):
        """Rejects a manual guard → creates rejection log and exits with code 1."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app,
            [
                "guard",
                "reject",
                "GUARD-007",
                "--target",
                str(adr_path),
                "--approver",
                "Tester",
                "--reason",
                "Nope",
            ],
        )
        assert result.exit_code == 1
        assert "REJECTED by Tester" in result.stdout
        assert "Nope" in result.stdout

        # Verify the rejection log was written
        log_file = (
            guard_mod.AUDIT_DIR
            / "approval-log"
            / f"GUARD-007_{adr_path.stem}.json"
        )
        assert log_file.exists()
        record = json.loads(log_file.read_text())
        assert record["guard_id"] == "GUARD-007"
        assert record["approver"] == "Tester"
        assert record["status"] == "rejected"
        assert record["reason"] == "Nope"

    def test_reject_invalid_guard_id(self, runner, app, guard_env):
        """With invalid guard ID → 'not found in profile'."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app,
            [
                "guard",
                "reject",
                "GUARD-999",
                "--target",
                str(adr_path),
                "--approver",
                "Tester",
                "--reason",
                "Bad",
            ],
        )
        assert result.exit_code == 1
        assert "not found in profile" in result.stdout

    def test_reject_without_approver(self, runner, app, guard_env):
        """Without --approver → '❌ --approver/-a is required'."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app,
            [
                "guard",
                "reject",
                "GUARD-007",
                "--target",
                str(adr_path),
                "--reason",
                "Nope",
            ],
        )
        assert result.exit_code == 1
        assert "❌" in result.stdout
        assert "approver" in result.stdout.lower()

    def test_reject_without_reason(self, runner, app, guard_env):
        """Rejects without --reason → uses default message, exits with code 1."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app,
            [
                "guard",
                "reject",
                "GUARD-007",
                "--target",
                str(adr_path),
                "--approver",
                "Tester",
            ],
        )
        assert result.exit_code == 1
        assert "REJECTED by Tester" in result.stdout
        assert "No reason provided" in result.stdout

    def test_reject_non_manual_guard(self, runner, app, guard_env):
        """Rejecting a non-manual guard → 'is not a manual guard' + exit code 1 (lines 562-563)."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app,
            [
                "guard",
                "reject",
                "GUARD-001",
                "--target",
                str(adr_path),
                "--approver",
                "Tester",
                "--reason",
                "Nope",
            ],
        )
        assert result.exit_code == 1
        assert "is not a manual guard" in result.stdout


# ── guard status ─────────────────────────────────────────────────────────


class TestGuardStatus:
    """Tests for ``guard status <target>``."""

    def test_status_mixed(self, runner, app, guard_env):
        """Shows guard status for target — some approved, some pending."""
        _tmp_path, adr_path = guard_env

        # Pre-approve GUARD-007 so it shows as APPROVED
        approval_dir = guard_mod.AUDIT_DIR / "approval-log"
        approval_dir.mkdir(parents=True)
        record = {
            "guard_id": "GUARD-007",
            "guard_name": "Stakeholder Sign-off",
            "target": str(adr_path),
            "approver": "Tester",
            "status": "approved",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        (approval_dir / f"GUARD-007_{adr_path.stem}.json").write_text(
            json.dumps(record, indent=2)
        )

        result = runner.invoke(app, ["guard", "status", str(adr_path)])
        assert result.exit_code == 0
        assert "Guard Status" in result.stdout

        # GUARD-007 should show as APPROVED by Tester
        assert "APPROVED by Tester" in result.stdout
        assert "GUARD-007" in result.stdout

        # Other guards should show as PENDING
        assert "PENDING" in result.stdout


# ── guard run with invalid target ────────────────────────────────────────


class TestGuardRunEdgeCases:
    """Edge cases for ``guard run``."""

    def test_run_invalid_target_path(self, runner, app, guard_env):
        """With --target pointing to non-existent file → error."""
        result = runner.invoke(
            app, ["guard", "run", "--target", "/nonexistent/path.toml"]
        )
        assert result.exit_code == 1
        assert "Cannot load artifact" in result.stdout

    def test_run_with_invalid_profile(self, runner, app, guard_env):
        """With invalid profile name → error."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app,
            [
                "guard",
                "run",
                "--profile",
                "nonexistent",
                "--target",
                str(adr_path),
            ],
        )
        assert result.exit_code == 2  # typer.BadParameter

    def test_run_with_unknown_guard_in_exec_order(self, runner, app, tmp_path):
        """When execution.order references a guard not in [[guards]] → warns (lines 389-390)."""
        monkeypatch = pytest.MonkeyPatch()

        monkeypatch.setattr(guard_mod, "GOV_DIR", tmp_path)
        monkeypatch.setattr(guard_mod, "AUDIT_DIR", tmp_path / "audit")

        # Guard spec with GUARD-XXX in order but NOT in [[guards]]
        spec_dir = tmp_path / "guards"
        spec_dir.mkdir(parents=True)
        spec = GUARD_SPEC_TOML.replace(
            '"GUARD-001", "GUARD-002", "GUARD-003", "GUARD-004", "GUARD-005", "GUARD-006", "GUARD-007", "GUARD-008", "GUARD-009"',
            '"GUARD-001", "GUARD-XXX"',
        )
        (spec_dir / "default.toml").write_text(spec)

        adr_path = tmp_path / "ADR-099.toml"
        adr_path.write_text(ADR_TOML)

        result = runner.invoke(app, ["guard", "run", "--target", str(adr_path)])
        assert result.exit_code == 0
        assert "GUARD-XXX" in result.stdout
        assert "not found in spec" in result.stdout

        monkeypatch.undo()

    def test_run_with_failing_blocking_guard_results_in_blocked(self, runner, app, guard_env, invalid_adr_path):
        """When a blocking guard FAILs → BLOCKED outcome + exit code 1 (lines 443/447-449)."""
        _tmp_path, _adr_path = guard_env
        result = runner.invoke(
            app, ["guard", "run", "--target", str(invalid_adr_path)]
        )
        assert result.exit_code == 1
        assert "FAILED" in result.stdout
        assert "BLOCKED" in result.stdout


# ── guard check edge cases ───────────────────────────────────────────────


class TestGuardCheckManual:
    """Tests for ``guard check`` on manual guards."""

    def test_check_manual_guard_shows_pending(self, runner, app, guard_env):
        """Checking a manual guard shows pending/⏳ status."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app, ["guard", "check", "GUARD-007", "--target", str(adr_path)]
        )
        assert result.exit_code == 0
        assert "Manual guard" in result.stdout
        assert "requires human approval" in result.stdout

    def test_check_returns_all_severity_levels(self, runner, app, guard_env):
        """Guard-005 (warning severity) runs and produces output."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app, ["guard", "check", "GUARD-005", "--target", str(adr_path)]
        )
        assert result.exit_code == 0
        assert "GUARD-005" in result.stdout
        assert "Review Date" in result.stdout

    def test_check_valid_guard_passes(self, runner, app, guard_env):
        """A guard that passes produces exit code 0."""
        _tmp_path, adr_path = guard_env
        result = runner.invoke(
            app, ["guard", "check", "GUARD-001", "--target", str(adr_path)]
        )
        assert result.exit_code == 0
        assert "GUARD-001" in result.stdout

    def test_check_failing_guard_exits_nonzero(self, runner, app, guard_env, invalid_adr_path):
        """A guard that produces FAIL issues exits with code 1."""
        result = runner.invoke(
            app, ["guard", "check", "GUARD-001", "--target", str(invalid_adr_path)]
        )
        assert result.exit_code == 1
        assert "GUARD-001" in result.stdout

    def test_check_invalid_target_path(self, runner, app, guard_env):
        """With --target pointing to non-existent file → 'Cannot load artifact'."""
        result = runner.invoke(
            app, ["guard", "check", "GUARD-001", "--target", "/nonexistent/path.toml"]
        )
        assert result.exit_code == 1
        assert "Cannot load artifact" in result.stdout

    def test_check_automated_guard_without_checker(self, runner, app, tmp_path):
        """An automated guard that has no registered checker → 'No checker implemented' (line 487)."""
        monkeypatch = pytest.MonkeyPatch()

        monkeypatch.setattr(guard_mod, "GOV_DIR", tmp_path)
        monkeypatch.setattr(guard_mod, "AUDIT_DIR", tmp_path / "audit")

        spec_dir = tmp_path / "guards"
        spec_dir.mkdir(parents=True)

        spec = """\
[metadata]
id = "default"
title = "No Checker Profile"
status = "active"
version = "1.0.0"
applies_to = ["*"]

[execution]
order = ["GUARD-010"]

[[guards]]
id = "GUARD-010"
name = "Unregistered Guard"
type = "automated"
severity = "warning"
"""
        (spec_dir / "default.toml").write_text(spec)

        adr_path = tmp_path / "ADR-099.toml"
        adr_path.write_text(ADR_TOML)

        result = runner.invoke(
            app, ["guard", "check", "GUARD-010", "--target", str(adr_path)]
        )
        assert result.exit_code == 0
        assert "No checker implemented" in result.stdout

        monkeypatch.undo()

"""
=============================================================
  Test Suite — Handoff Confirmation (workers/handoff-confirm.py)
=============================================================
  ทดสอบ:
    - CLI argument parsing
    - Confirmation record building
    - File saving/reading
    - Status validation
    - Handoff file auto-resolution
    - Schema compliance
=============================================================
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest

from workers.handoff_confirm import (
    CONFIRMATIONS_DIR,
    VALID_STATUSES,
    _now_iso,
    _timestamp_slug,
    build_confirmation,
    build_parser,
    main,
    save_confirmation,
    validate_status,
)


# ---- Fixtures -----------------------------------------------------------


@pytest.fixture
def sample_handoff_file(tmp_path: Path) -> str:
    """Create a sample handoff JSON file in a date subdirectory."""
    date_dir = tmp_path / "bus" / "dispatch" / "2026-07-20"
    date_dir.mkdir(parents=True, exist_ok=True)

    handoff_data = {
        "handoff": {
            "id": "HANDOFF-001",
            "from": "ceo",
            "to": "architect-songsak",
            "work_item": "ออกแบบระบบ Skill Routes",
            "status": "ready",
            "summary": "เตรียม spec เสร็จ พร้อมส่ง architect",
            "pending": ["สร้าง routes ใน busd", "deploy สู่ production"],
            "deadline": "2026-07-25",
            "priority": "P1",
        }
    }

    filepath = date_dir / "HANDOFF-001.json"
    with open(filepath, "w") as f:
        json.dump(handoff_data, f, indent=2)

    return str(tmp_path)


@pytest.fixture
def sample_command_file(tmp_path: Path) -> str:
    """Create a sample command dispatch JSON file."""
    date_dir = tmp_path / "bus" / "dispatch" / "2026-07-20"
    date_dir.mkdir(parents=True, exist_ok=True)

    cmd_data = {
        "command": {
            "id": "CMD-042",
            "from": "auto-triage",
            "to": "engineering",
            "title": "แก้ bug login page",
            "priority": "P1",
        },
        "status": "dispatched",
    }

    filepath = date_dir / "CMD-042.json"
    with open(filepath, "w") as f:
        json.dump(cmd_data, f, indent=2)

    return str(tmp_path)


# ---- Tests: Validation --------------------------------------------------


class TestValidation:
    """Status validation tests."""

    def test_valid_statuses(self) -> None:
        """All valid statuses pass validation."""
        for status in VALID_STATUSES:
            validate_status(status)  # should not raise

    def test_invalid_status_raises(self) -> None:
        """Invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            validate_status("invalid_status")

    def test_empty_status_raises(self) -> None:
        """Empty string status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            validate_status("")


# ---- Tests: Helper Functions -------------------------------------------


class TestHelpers:
    """Helper function tests."""

    def test_now_iso_format(self) -> None:
        """_now_iso() returns ISO-8601 formatted string."""
        result = _now_iso()
        assert "T" in result

    def test_timestamp_slug_format(self) -> None:
        """_timestamp_slug() returns compact YYYYMMDDTHHMMSS."""
        result = _timestamp_slug()
        assert len(result) == 15  # YYYYMMDDTHHMMSS
        assert "T" in result


# ---- Tests: Build Confirmation -----------------------------------------


class TestBuildConfirmation:
    """Confirmation record building tests."""

    def test_acknowledged_status(self) -> None:
        """Acknowledged status sets all three checklist items to True."""
        record = build_confirmation(
            handoff_id="HANDOFF-001",
            to_dept="engineering",
            status="acknowledged",
            from_dept="ceo",
            work_item="Implement login API",
        )

        assert record["handoff_id"] == "HANDOFF-001"
        assert record["from"] == "ceo"
        assert record["to"] == "engineering"
        assert record["status"] == "acknowledged"
        assert record["acknowledge_context"] is True
        assert record["understand_pending"] is True
        assert record["take_over"] is True
        assert record["confirmed_by"] == "engineering"
        assert "confirmed_at" in record

    def test_rejected_status(self) -> None:
        """Rejected status sets all three checklist items to False."""
        record = build_confirmation(
            handoff_id="HANDOFF-002",
            to_dept="ceo",
            status="rejected",
            from_dept="engineering",
            work_item="Refactor auth module",
            notes="context ไม่ครบ ไม่มี deadline",
        )

        assert record["status"] == "rejected"
        assert record["acknowledge_context"] is False
        assert record["understand_pending"] is False
        assert record["take_over"] is False
        assert record["notes"] == "context ไม่ครบ ไม่มี deadline"

    def test_need_clarify_status(self) -> None:
        """need_clarify acknowledges context but not take over."""
        record = build_confirmation(
            handoff_id="HANDOFF-003",
            to_dept="architect-songsak",
            status="need_clarify",
            from_dept="product",
            work_item="Design system migration",
            notes="ขอ clarification เรื่อง API contract",
        )

        assert record["status"] == "need_clarify"
        assert record["acknowledge_context"] is True
        assert record["understand_pending"] is False
        assert record["take_over"] is False

    def test_auto_resolve_unknown_when_no_file(self) -> None:
        """When handoff file doesn't exist, from defaults to 'unknown'."""
        record = build_confirmation(
            handoff_id="HANDOFF-999",
            to_dept="engineering",
            status="acknowledged",
        )

        assert record["from"] == "unknown"
        assert record["work_item"] == "HANDOFF-999"

    def test_notes_default_empty(self) -> None:
        """Default notes is empty string."""
        record = build_confirmation(
            handoff_id="HANDOFF-004",
            to_dept="engineering",
            status="acknowledged",
            from_dept="ceo",
            work_item="Test",
        )

        assert record["notes"] == ""


# ---- Tests: Save Confirmation -------------------------------------------


class TestSaveConfirmation:
    """Confirmation file saving tests."""

    def test_save_creates_file(self, monkeypatch) -> None:
        """save_confirmation creates a JSON file in confirmations dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_confirm_dir = os.path.join(tmpdir, "confirmations")
            monkeypatch.setattr(
                "workers.handoff_confirm.CONFIRMATIONS_DIR", fake_confirm_dir
            )

            record = build_confirmation(
                handoff_id="HANDOFF-005",
                to_dept="engineering",
                status="acknowledged",
                from_dept="ceo",
                work_item="Test save",
            )

            filepath = save_confirmation(record)

            assert os.path.isfile(filepath)
            assert fake_confirm_dir in filepath
            assert "HANDOFF-005" in filepath
            assert "acknowledged" in filepath

            with open(filepath, "r") as f:
                saved = json.load(f)
            assert saved["handoff_id"] == "HANDOFF-005"
            assert saved["status"] == "acknowledged"

    def test_dry_run_does_not_create_file(self, monkeypatch) -> None:
        """Dry-run mode does not actually write the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_confirm_dir = os.path.join(tmpdir, "confirmations")
            monkeypatch.setattr(
                "workers.handoff_confirm.CONFIRMATIONS_DIR", fake_confirm_dir
            )

            record = build_confirmation(
                handoff_id="HANDOFF-006",
                to_dept="engineering",
                status="acknowledged",
                from_dept="ceo",
                work_item="Dry run test",
            )

            filepath = save_confirmation(record, dry_run=True)

            assert not os.path.isfile(filepath)

    def test_save_creates_dir_if_not_exists(self, monkeypatch) -> None:
        """save_confirmation creates the confirmations directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "a", "b", "c")
            monkeypatch.setattr(
                "workers.handoff_confirm.CONFIRMATIONS_DIR", nested_dir
            )

            record = build_confirmation(
                handoff_id="HANDOFF-007",
                to_dept="engineering",
                status="acknowledged",
                from_dept="ceo",
                work_item="Dir create test",
            )

            filepath = save_confirmation(record)
            assert os.path.isdir(nested_dir)
            assert os.path.isfile(filepath)


# ---- Tests: CLI Argument Parsing ----------------------------------------


class TestCLI:
    """CLI argument parsing tests."""

    def test_parser_requires_handoff(self) -> None:
        """--handoff is required."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_parser_requires_to(self) -> None:
        """--to is required."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--handoff", "HANDOFF-001"])

    def test_parser_requires_status(self) -> None:
        """--status is required."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([
                "--handoff", "HANDOFF-001",
                "--to", "engineering",
            ])

    def test_parser_accepts_valid_args(self) -> None:
        """All required arguments parse correctly."""
        parser = build_parser()
        args = parser.parse_args([
            "--handoff", "HANDOFF-001",
            "--to", "engineering",
            "--status", "acknowledged",
            "--notes", "รับทราบ",
        ])

        assert args.handoff == "HANDOFF-001"
        assert args.to_dept == "engineering"
        assert args.status == "acknowledged"
        assert args.notes == "รับทราบ"
        assert args.dry_run is False

    def test_parser_accepts_dry_run(self) -> None:
        """--dry-run flag is accepted."""
        parser = build_parser()
        args = parser.parse_args([
            "--handoff", "HANDOFF-001",
            "--to", "engineering",
            "--status", "acknowledged",
            "--dry-run",
        ])
        assert args.dry_run is True

    def test_parser_validates_status_choice(self) -> None:
        """--status must be one of the valid choices."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([
                "--handoff", "HANDOFF-001",
                "--to", "engineering",
                "--status", "invalid",
            ])

    def test_parser_accepts_optional_from(self) -> None:
        """--from-department is optional."""
        parser = build_parser()
        args = parser.parse_args([
            "--handoff", "HANDOFF-001",
            "--to", "engineering",
            "--status", "acknowledged",
            "--from-department", "ceo",
        ])
        assert args.from_dept == "ceo"


# ---- Tests: Integration with Handoff File -------------------------------


class TestHandoffFileResolution:
    """Tests for auto-resolving metadata from handoff files."""

    def test_resolve_from_handoff_format(
        self, monkeypatch, sample_handoff_file
    ) -> None:
        """Auto-resolve from_dept and work_item from handoff JSON."""
        monkeypatch.setattr(
            "workers.handoff_confirm.DISPATCH_DIR",
            os.path.join(sample_handoff_file, "bus", "dispatch"),
        )

        record = build_confirmation(
            handoff_id="HANDOFF-001",
            to_dept="architect-songsak",
            status="acknowledged",
        )

        assert record["from"] == "ceo"
        assert record["work_item"] == "ออกแบบระบบ Skill Routes"

    def test_resolve_from_command_format(
        self, monkeypatch, sample_command_file
    ) -> None:
        """Auto-resolve from command dispatch format."""
        monkeypatch.setattr(
            "workers.handoff_confirm.DISPATCH_DIR",
            os.path.join(sample_command_file, "bus", "dispatch"),
        )

        record = build_confirmation(
            handoff_id="CMD-042",
            to_dept="engineering",
            status="acknowledged",
        )

        assert record["from"] == "auto-triage"
        assert "bug" in record["work_item"]
        assert "login" in record["work_item"]

    def test_unknown_handoff_defaults(self) -> None:
        """Unknown handoff ID resolves to 'unknown' defaults."""
        record = build_confirmation(
            handoff_id="HANDOFF-999",
            to_dept="engineering",
            status="acknowledged",
        )

        assert record["from"] == "unknown"
        assert record["work_item"] == "HANDOFF-999"


# ---- Tests: CLI Main Integration ----------------------------------------


class TestCLIMain:
    """Integration tests for CLI main()."""

    def test_main_success(self, monkeypatch, tmp_path: Path) -> None:
        """main() completes successfully with valid args."""
        fake_confirm_dir = os.path.join(str(tmp_path), "confirmations")
        monkeypatch.setattr(
            "workers.handoff_confirm.CONFIRMATIONS_DIR", fake_confirm_dir
        )

        test_args = [
            "handoff-confirm.py",
            "--handoff", "HANDOFF-001",
            "--to", "engineering",
            "--status", "acknowledged",
            "--from-department", "ceo",
            "--work-item", "Integration test",
            "--quiet",
        ]
        with patch.object(sys, "argv", test_args):
            main()  # should not raise

        files = os.listdir(fake_confirm_dir)
        assert len(files) == 1
        assert "HANDOFF-001" in files[0]
        assert "acknowledged" in files[0]

    def test_main_dry_run(self, monkeypatch, tmp_path: Path, capsys) -> None:
        """main() with --dry-run doesn't create files."""
        fake_confirm_dir = os.path.join(str(tmp_path), "confirmations")
        monkeypatch.setattr(
            "workers.handoff_confirm.CONFIRMATIONS_DIR", fake_confirm_dir
        )

        test_args = [
            "handoff-confirm.py",
            "--handoff", "HANDOFF-002",
            "--to", "engineering",
            "--status", "acknowledged",
            "--from-department", "ceo",
            "--work-item", "Dry run test",
            "--dry-run",
        ]
        with patch.object(sys, "argv", test_args):
            main()

        captured = capsys.readouterr()
        assert "Dry-run" in captured.out
        if os.path.isdir(fake_confirm_dir):
            assert len(os.listdir(fake_confirm_dir)) == 0

    def test_main_invalid_status_exits(self) -> None:
        """main() exits with code 1 on invalid status."""
        test_args = [
            "handoff-confirm.py",
            "--handoff", "HANDOFF-001",
            "--to", "engineering",
            "--status", "invalid_status",
        ]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

    def test_main_machine_readable_output(
        self, monkeypatch, tmp_path: Path, capsys
    ) -> None:
        """main() outputs CONFIRMED and FILE lines for pipeline."""
        fake_confirm_dir = os.path.join(str(tmp_path), "confirmations")
        monkeypatch.setattr(
            "workers.handoff_confirm.CONFIRMATIONS_DIR", fake_confirm_dir
        )

        test_args = [
            "handoff-confirm.py",
            "--handoff", "HANDOFF-001",
            "--to", "engineering",
            "--status", "acknowledged",
            "--from-department", "ceo",
            "--work-item", "Pipeline test",
            "--quiet",
        ]
        with patch.object(sys, "argv", test_args):
            main()

        captured = capsys.readouterr()
        assert "CONFIRMED=acknowledged" in captured.out
        assert "FILE=" in captured.out


# ---- Tests: Confirmation Record Schema ----------------------------------


class TestRecordSchema:
    """Confirmation record schema compliance tests."""

    REQUIRED_FIELDS = [
        "handoff_id",
        "from",
        "to",
        "work_item",
        "confirmed_by",
        "confirmed_at",
        "status",
        "acknowledge_context",
        "understand_pending",
        "take_over",
        "notes",
    ]

    def test_record_has_all_required_fields(self) -> None:
        """Confirmation record must have all schema fields."""
        record = build_confirmation(
            handoff_id="HANDOFF-001",
            to_dept="engineering",
            status="acknowledged",
            from_dept="ceo",
            work_item="Test",
        )

        for field in self.REQUIRED_FIELDS:
            assert field in record, f"Missing field: {field}"

        assert len(record) == len(self.REQUIRED_FIELDS)

    def test_record_types_are_correct(self) -> None:
        """Each field has the correct type."""
        record = build_confirmation(
            handoff_id="HANDOFF-001",
            to_dept="engineering",
            status="acknowledged",
            from_dept="ceo",
            work_item="Test",
        )

        assert isinstance(record["handoff_id"], str)
        assert isinstance(record["from"], str)
        assert isinstance(record["to"], str)
        assert isinstance(record["work_item"], str)
        assert isinstance(record["confirmed_by"], str)
        assert isinstance(record["confirmed_at"], str)
        assert isinstance(record["status"], str)
        assert isinstance(record["acknowledge_context"], bool)
        assert isinstance(record["understand_pending"], bool)
        assert isinstance(record["take_over"], bool)
        assert isinstance(record["notes"], str)

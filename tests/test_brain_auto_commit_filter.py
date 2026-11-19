"""Regression tests for BrainAutoCommitLoop's path filter (incident 64344c4).

The loop used a substring test ("bus/" in path), so every ``central_bus/``
path matched and the hourly L4 loop committed source code plus ~97 MB of raw
owner footage. Selection must be anchored to top-level brain dirs, and must
survive the porcelain shapes emitted for deletes, renames, and quoted paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loop_runner.loops.brain_auto_commit import _is_brain_path, _status_path


def _select(status: str) -> list[str]:
    """Mirror of BrainAutoCommitLoop.run()'s selection step."""
    return [
        path
        for line in status.splitlines()
        if line.strip()
        for path in [_status_path(line)]
        if _is_brain_path(path)
    ]


class TestIsBrainPath:
    def test_central_bus_source_not_selected(self):
        assert _is_brain_path("central_bus/main.py") is False

    def test_incident_media_not_selected(self):
        assert (
            _is_brain_path(
                "central_bus/content/owner_footage_staged_20261113/01_130408.mp4"
            )
            is False
        )

    def test_top_level_bus_selected(self):
        assert _is_brain_path("bus/reports/x.md") is True
        assert _is_brain_path("bus/evidence/incident.md") is True

    def test_brain_owned_dirs_selected(self):
        for path in (
            "brain/x.md",
            "memory/x.json",
            "decisions/x.md",
            ".claude/rules/x.md",
        ):
            assert _is_brain_path(path) is True

    def test_lookalike_names_not_selected(self):
        assert _is_brain_path("my_brain/x.md") is False
        assert _is_brain_path("rebus/x.md") is False


class TestPorcelainShapes:
    def test_deleted_file_parses_and_matches(self):
        assert _status_path(" D brain/x.md") == "brain/x.md"
        assert _select(" D brain/x.md") == ["brain/x.md"]

    def test_staged_delete_does_not_crash(self):
        assert _status_path("D  brain/x.md") == "brain/x.md"

    def test_rename_uses_destination(self):
        line = "R  bus/reports/x.md -> bus/reports/y.md"
        assert _status_path(line) == "bus/reports/y.md"
        assert _select(line) == ["bus/reports/y.md"]

    def test_rename_out_of_brain_not_selected(self):
        line = "R  brain/x.md -> central_bus/content/x.py"
        assert _select(line) == []

    def test_quoted_path_is_unquoted(self):
        assert _select('?? "brain/with space.md"') == ["brain/with space.md"]

    def test_mixed_status_selects_only_brain_paths(self):
        status = "\n".join(
            [
                " M brain/learnt.md",
                "?? central_bus/content/owner_footage_staged_20261113/01_130408.mp4",
                " D bus/reports/gone.md",
                '?? "central_bus/content/campaign-...-เลข.md"',
                "R  bus/reports/x.md -> bus/reports/y.md",
                "?? scripts/probe.py",
            ]
        )
        assert _select(status) == [
            "brain/learnt.md",
            "bus/reports/gone.md",
            "bus/reports/y.md",
        ]

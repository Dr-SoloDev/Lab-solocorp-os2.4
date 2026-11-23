"""Version SSoT gate — one version, declared once.

Incident being prevented: ``central_bus/main.py`` reported ``0.6.2`` (FastAPI
``version`` + startup log) while ``central_bus/health.py`` kept serving
``VERSION = "0.6.0"`` since 2026-07-06. ``/v1/health`` told operators a stale
version and ``central_bus/tests/test_integration.py`` had the stale literal
baked in, so the test suite *enforced* the drift.

Single source of truth: ``central_bus.__version__``.
- ``central_bus.main.app.version`` must equal it.
- ``central_bus.health.VERSION`` must equal it.
- No module may re-introduce a local version literal.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import central_bus
from central_bus import health, main

REPO_ROOT = Path(__file__).resolve().parent.parent
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")


class TestVersionIsOneValue:
    def test_package_declares_a_semver(self) -> None:
        assert isinstance(central_bus.__version__, str)
        assert SEMVER_RE.match(central_bus.__version__), central_bus.__version__

    def test_health_matches_package_version(self) -> None:
        assert health.VERSION == central_bus.__version__

    def test_fastapi_app_matches_package_version(self) -> None:
        assert main.app.version == central_bus.__version__

    def test_all_three_agree(self) -> None:
        assert health.VERSION == main.app.version == central_bus.__version__

    def test_fastapi_title_is_derived_from_version(self) -> None:
        # title used to be hardcoded "Central Bus v0.6" — derivable drift too.
        assert main.app.title == f"Central Bus v{central_bus.__version__}"

    def test_startup_log_uses_version_placeholder(self) -> None:
        source = (REPO_ROOT / "central_bus" / "main.py").read_text(encoding="utf-8")
        assert "Central Bus v%s starting up" in source
        log_lines = [ln for ln in source.splitlines() if ln.strip().startswith("log.")]
        assert not any(re.search(r"Central Bus v\d+\.\d+", ln) for ln in log_lines), (
            "hardcoded version in a main.py log line"
        )


class TestNoVersionLiteralsReintroduced:
    """Anti-drift: the literals that caused the incident must not come back."""

    def test_health_has_no_local_version_literal(self) -> None:
        source = (REPO_ROOT / "central_bus" / "health.py").read_text(encoding="utf-8")
        match = re.search(r'^VERSION\s*=\s*"([^"]+)"', source, re.MULTILINE)
        assert match is None, (
            f'central_bus/health.py re-declares VERSION = "{match.group(1) if match else ""}" — '
            "import central_bus.__version__ instead"
        )

    def test_main_has_no_fastapi_version_literal(self) -> None:
        source = (REPO_ROOT / "central_bus" / "main.py").read_text(encoding="utf-8")
        match = re.search(r"^\s{4}version=\"([^\"]+)\"", source, re.MULTILINE)
        assert match is None, (
            f'central_bus/main.py hardcodes version="{match.group(1) if match else ""}" '
            "in the FastAPI factory — use BUS_VERSION"
        )

    def test_package_declares_exactly_one_version_literal(self) -> None:
        source = (REPO_ROOT / "central_bus" / "__init__.py").read_text(encoding="utf-8")
        literals = re.findall(r'^__version__\s*=\s*"([^"]+)"', source, re.MULTILINE)
        assert len(literals) == 1, (
            f"expected exactly one __version__ literal, got {literals}"
        )


class TestHealthEndpointReportsPackageVersion:
    def test_health_payload_carries_current_version(self) -> None:
        """The observed drift: /v1/health served health.VERSION (0.6.0)."""
        import asyncio

        from central_bus.facts import FactsService
        from central_bus.health import get_health
        from central_bus.queue import SQLiteQueueManager
        from central_bus.router import RoutingEngine

        class _FakeDb:
            async def fetch_one(self, _query: str):
                return {"ok": 1}

        class _FakeQueue:
            async def count_pending(self) -> int:
                return 0

            async def count_failed(self) -> int:
                return 0

            async def count_dead_letters(self) -> int:
                return 0

        class _FakeFacts:
            async def count_facts(self) -> int:
                return 0

        class _FakeEngine:
            async def count_rules(self) -> int:
                return 0

        payload = asyncio.run(
            get_health(
                _FakeDb(),  # type: ignore[arg-type]
                _FakeQueue(),  # type: ignore[arg-type]
                _FakeFacts(),  # type: ignore[arg-type]
                _FakeEngine(),  # type: ignore[arg-type]
                started_at=0.0,
            )
        )
        assert isinstance(payload, dict)
        assert payload["version"] == central_bus.__version__

    def test_queue_manager_and_engine_classes_are_the_real_ones(self) -> None:
        """Guard the fakes above stay substitutable (signature drift)."""
        from central_bus.facts import FactsService
        from central_bus.queue import SQLiteQueueManager
        from central_bus.router import RoutingEngine

        assert hasattr(FactsService, "count_facts")
        assert hasattr(SQLiteQueueManager, "count_pending")
        assert hasattr(RoutingEngine, "count_rules")
        pytest.importorskip("fastapi")

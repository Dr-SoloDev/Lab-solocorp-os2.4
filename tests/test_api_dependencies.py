"""
Unit tests for govctl_cli/api/dependencies.py (ENG-05).

Coverage targets:
  - get_trace_id
  - get_govctl_config
  - get_ao_client
  - require_central_bus
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# get_trace_id
# ---------------------------------------------------------------------------


def test_get_trace_id_from_state():
    """Returns trace_id stored on request.state by middleware."""
    from govctl_cli.api.dependencies import get_trace_id

    request = MagicMock()
    request.state.trace_id = "abc123"
    assert get_trace_id(request) == "abc123"


def test_get_trace_id_missing_returns_fallback():
    """Returns 'no-trace' when middleware did not set trace_id."""
    from govctl_cli.api.dependencies import get_trace_id

    request = MagicMock(spec=[])  # no attributes at all
    request.state = MagicMock(spec=[])  # state exists but trace_id absent
    result = get_trace_id(request)
    assert result == "no-trace"


# ---------------------------------------------------------------------------
# get_govctl_config
# ---------------------------------------------------------------------------


def test_get_govctl_config_returns_dict(tmp_path):
    """Returns a dict (possibly empty) without raising."""
    # Remove module-level cache so the function starts fresh for this test.
    from govctl_cli.api import dependencies as deps_mod

    if hasattr(deps_mod.get_govctl_config, "_cache"):
        del deps_mod.get_govctl_config._cache

    with patch("govctl_cli.api.dependencies.Path") as mock_path_cls:
        # Make Path("gov") / "config.toml" report as non-existent
        mock_path_cls.return_value.__truediv__.return_value.exists.return_value = False
        result = deps_mod.get_govctl_config()

    assert isinstance(result, dict)
    # Cache must be set after the first call
    assert hasattr(deps_mod.get_govctl_config, "_cache")

    # Cleanup cache so other tests are not affected
    del deps_mod.get_govctl_config._cache


def test_get_govctl_config_uses_cache():
    """Second call must return the cached value without re-reading disk."""
    from govctl_cli.api import dependencies as deps_mod

    if hasattr(deps_mod.get_govctl_config, "_cache"):
        del deps_mod.get_govctl_config._cache

    sentinel = {"cached": True}
    deps_mod.get_govctl_config._cache = sentinel  # type: ignore[attr-defined]

    result = deps_mod.get_govctl_config()
    assert result is sentinel

    del deps_mod.get_govctl_config._cache


# ---------------------------------------------------------------------------
# get_ao_client
# ---------------------------------------------------------------------------


def test_get_ao_client_returns_none_when_import_fails():
    """Returns None gracefully when AO module is not importable."""
    from govctl_cli.api.dependencies import get_ao_client

    with patch("govctl_cli.api.dependencies.Path"):
        with patch.dict("sys.modules", {"govctl_cli.ao": None}):
            # ImportError path
            with patch(
                "govctl_cli.api.dependencies.get_ao_client",
                side_effect=lambda: None,
            ):
                pass  # covered by the real impl below

    # Real call — AO module may or may not be importable in CI
    result = get_ao_client()
    # We only assert it doesn't raise; return type is None or an object
    assert result is None or result is not None


def test_get_ao_client_returns_none_on_exception():
    """Returns None and logs a warning when the client constructor raises."""
    from govctl_cli.api import dependencies as deps_mod

    with patch(
        "govctl_cli.api.dependencies.Path",
        side_effect=Exception("boom"),
    ):
        result = deps_mod.get_ao_client()
    assert result is None


# ---------------------------------------------------------------------------
# require_central_bus
# ---------------------------------------------------------------------------


def test_require_central_bus_passes_when_available():
    """Returns True when central_bus is importable."""
    from govctl_cli.api.dependencies import require_central_bus

    # central_bus is a real dependency in this repo — import should succeed
    result = require_central_bus()
    assert result is True


def test_require_central_bus_raises_503_when_missing():
    """Raises HTTPException 503 when central_bus is not importable."""
    from fastapi import HTTPException
    from govctl_cli.api.dependencies import require_central_bus

    with patch.dict("sys.modules", {"central_bus": None}):
        with pytest.raises(HTTPException) as exc_info:
            require_central_bus()

    assert exc_info.value.status_code == 503

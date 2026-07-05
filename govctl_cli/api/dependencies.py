"""
Dependency injection for FastAPI routes.

Provides shared dependencies: AO client, Central Bus access, config.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import Request, HTTPException

log = logging.getLogger("govctl.api.deps")


# ═══════════════════════════════════════════════════════════════════════
# Trace ID dependency
# ═══════════════════════════════════════════════════════════════════════


def get_trace_id(request: Request) -> str:
    """Get the current request's trace_id from middleware state.

    Usage:
        @router.get("/example")
        async def example(trace_id: str = Depends(get_trace_id)):
            ...
    """
    return getattr(request.state, "trace_id", "no-trace")


# ═══════════════════════════════════════════════════════════════════════
# Config dependency
# ═══════════════════════════════════════════════════════════════════════


def get_govctl_config() -> dict:
    """Load govctl configuration from gov/config.toml.

    Cached at module level for performance.
    Returns empty dict if not found.
    """
    if hasattr(get_govctl_config, "_cache"):
        return get_govctl_config._cache  # type: ignore[attr-defined]

    try:
        import tomllib
        config_path = Path("gov") / "config.toml"
        if config_path.exists():
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
            get_govctl_config._cache = config  # type: ignore[attr-defined]
            return config
    except (ImportError, tomllib.TOMLDecodeError, OSError) as exc:
        log.debug("Failed to load config: %s", exc)

    get_govctl_config._cache = {}  # type: ignore[attr-defined]
    return {}


# ═══════════════════════════════════════════════════════════════════════
# AO Client dependency
# ═══════════════════════════════════════════════════════════════════════


def get_ao_client():
    """Get an AOClient instance configured from gov/ao_config.toml.

    Returns None if AO module is not available.
    """
    try:
        from govctl_cli.ao import get_configured_client
        return get_configured_client(Path("gov") / "ao_config.toml")
    except ImportError:
        return None
    except Exception as exc:
        log.warning("Failed to create AO client: %s", exc)
        return None


# ═══════════════════════════════════════════════════════════════════════
# Central Bus availability check
# ═══════════════════════════════════════════════════════════════════════


def require_central_bus():
    """Dependency that ensures Central Bus is importable.

    Raises 503 if central_bus module is not available.
    """
    try:
        import central_bus  # noqa: F401
        return True
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Central Bus module is not available in this environment",
        )

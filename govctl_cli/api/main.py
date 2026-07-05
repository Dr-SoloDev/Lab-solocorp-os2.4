"""
SoloCorp OS Admin API — Entry Point

Usage:
    # Via Python module
    python -m govctl_cli.api.main

    # Via uvicorn
    uvicorn govctl_cli.api.main:app --reload --port 8080
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# ── Version ───────────────────────────────────────────────────────────

try:
    from .. import __version__ as GOVCTL_VERSION
except ImportError:
    GOVCTL_VERSION = "0.1.0"

# ── Logging ───────────────────────────────────────────────────────────

LOG_LEVEL = os.getenv("GOVCTL_API_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

log = logging.getLogger("govctl.api")


# ═══════════════════════════════════════════════════════════════════════
# App factory
# ═══════════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    """Factory function to create and configure the FastAPI application.

    This is import-safe — importing this module does NOT auto-start.
    Call ``uvicorn govctl_cli.api.main:app`` or ``app = create_app()``.
    """
    is_prod = os.getenv("GOVCTL_API_ENV") == "production"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Startup / shutdown lifecycle handler."""
        log.info("SoloCorp OS Admin API starting — version %s", GOVCTL_VERSION)
        gov_dir = Path("gov")
        if not gov_dir.exists():
            log.warning("gov/ directory not found — run 'govctl init' first")
        else:
            adr_count = len(list((gov_dir / "adr").glob("*.toml"))) if (gov_dir / "adr").exists() else 0
            rfc_count = len(list((gov_dir / "rfc").glob("*.toml"))) if (gov_dir / "rfc").exists() else 0
            log.info(
                "Governance artifacts: %d ADRs, %d RFCs",
                adr_count, rfc_count,
            )
        try:
            from central_bus.queue import QUEUE_DIR
            if QUEUE_DIR.exists():
                total = sum(
                    len(f.read_text().splitlines())
                    for f in QUEUE_DIR.glob("*.jsonl")
                    if f.exists()
                )
                log.info("Central Bus queue: ~%d messages", total)
        except ImportError:
            log.info("Central Bus module not available")

        yield

        log.info("SoloCorp OS Admin API shutting down")

    app = FastAPI(
        title="SoloCorp OS Admin API",
        description=(
            "REST API for SoloCorp OS governance, agent orchestration, "
            "pipeline monitoring, and system health.\n\n"
            "## Quick Links\n"
            "- **Dashboard**: [Web UI](/)"
            "- **Health**: [GET /api/v1/health](/api/v1/health)\n"
            "- **Metrics**: [GET /api/v1/metrics](/api/v1/metrics)\n"
        ),
        version=GOVCTL_VERSION,
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
        lifespan=lifespan,
    )

    # ── Static files ──────────────────────────────────────────────────
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        log.info("Static directory mounted: %s", static_dir)

    # ── Middleware ────────────────────────────────────────────────────
    # Order matters — see middleware.py for details
    from .middleware import register_middleware
    register_middleware(app)

    # ── Routes ────────────────────────────────────────────────────────
    from .routes.governance import router as gov_router
    from .routes.agents import router as agent_router
    from .routes.pipeline import router as pipeline_router
    from .routes.monitoring import router as monitoring_router

    app.include_router(gov_router)
    app.include_router(agent_router)
    app.include_router(pipeline_router)
    app.include_router(monitoring_router)

    # ── Root — serve dashboard or redirect ────────────────────────────

    @app.get("/", include_in_schema=False)
    async def root():
        index_path = static_dir / "index.html"
        if index_path.exists():
            return HTMLResponse(index_path.read_text(encoding="utf-8"))
        return RedirectResponse(url="/docs")

    @app.get("/api/v1", include_in_schema=False)
    async def api_root():
        return {
            "name": "SoloCorp OS Admin API",
            "version": GOVCTL_VERSION,
            "endpoints": {
                "governance": "/api/v1/gov/adrs",
                "agents": "/api/v1/agents",
                "pipeline": "/api/v1/pipeline/status",
                "monitoring": "/api/v1/health",
                "dashboard": "/",
                "docs": "/docs",
            },
        }

    return app


# ═══════════════════════════════════════════════════════════════════════
# Direct invocation
# ═══════════════════════════════════════════════════════════════════════

app = create_app()


def main():
    """Run via ``python -m govctl_cli.api.main``."""
    import uvicorn

    port = int(os.getenv("GOVCTL_API_PORT", "8765"))
    host = os.getenv("GOVCTL_API_HOST", "127.0.0.1")
    reload = os.getenv("GOVCTL_API_RELOAD", "false").lower() == "true"

    log.info("Starting API server at http://%s:%d", host, port)
    uvicorn.run(
        "govctl_cli.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()

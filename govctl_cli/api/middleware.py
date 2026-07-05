"""
API Middleware — logging, CORS, request tracing, API key auth.

All middleware is registered in create_app() via app.add_middleware()
or app.middleware() decorator.
"""

from __future__ import annotations

import time
import uuid
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("govctl.api.middleware")


# ═══════════════════════════════════════════════════════════════════════
# Request tracing — adds X-Trace-Id to every response
# ═══════════════════════════════════════════════════════════════════════


class TracingMiddleware(BaseHTTPMiddleware):
    """Adds a unique trace_id to every request/response.

    The trace_id is generated if not provided via X-Trace-Id header,
    and returned in the response header for correlation.
    """

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id", uuid.uuid4().hex[:12])
        request.state.trace_id = trace_id

        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

        return response


# ═══════════════════════════════════════════════════════════════════════
# Request logging
# ═══════════════════════════════════════════════════════════════════════


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs all API requests with method, path, status, timing."""

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        log.info(
            "%s %s → %d (%dms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request.state.trace_id,
        )

        return response


# ═══════════════════════════════════════════════════════════════════════
# API Key authentication guard
# ═══════════════════════════════════════════════════════════════════════


class APIAuthMiddleware(BaseHTTPMiddleware):
    """Optional API key authentication for write operations.

    Reads the API key from gov/config.toml or a default.
    Skips auth for GET and OPTIONS requests.
    """

    def __init__(self, app: FastAPI, api_key: str | None = None):
        super().__init__(app)
        self._api_key = api_key or self._load_api_key()

    @staticmethod
    def _load_api_key() -> str | None:
        """Load API key from gov/config.toml."""
        try:
            import tomllib
            config_path = Path("gov") / "config.toml"
            if config_path.exists():
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                return config.get("api", {}).get("key")
        except Exception:
            pass
        return None

    async def dispatch(self, request: Request, call_next):
        # Skip auth for safe methods
        if request.method in ("GET", "OPTIONS", "HEAD"):
            return await call_next(request)

        # Check API key
        provided = request.headers.get("X-API-Key")
        expected = self._api_key

        if expected and provided != expected:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Invalid or missing API key. "
                                   "Provide X-API-Key header.",
                    }
                },
            )

        return await call_next(request)


# ═══════════════════════════════════════════════════════════════════════
# Registration helper
# ═══════════════════════════════════════════════════════════════════════


from pathlib import Path  # noqa: E402 (needed for _load_api_key)


def register_middleware(app: FastAPI) -> None:
    """Register all middleware on a FastAPI application.

    Order matters — execute in this sequence:
        1. CORS (outermost — before any processing)
        2. Tracing (captures trace_id early)
        3. Auth (validates before request processing)
        4. Logging (logs after response is generated)
    """
    # CORS — permissive for local dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Trace-Id", "X-Response-Time-Ms"],
    )

    # Tracing
    app.add_middleware(TracingMiddleware)

    # API Auth (optional — only enforces if key is configured)
    app.add_middleware(APIAuthMiddleware)

    # Request logging (last = wraps the response)
    app.add_middleware(RequestLoggingMiddleware)

"""FastAPI application for the local SoloCorp App shell (Phase 1).

Pages: CEO chat (placeholder), Modules, Task history, Settings.
Mutations: enable/disable a module, health check, save provider settings.

Everything here is server-rendered with Jinja and shipped with two small
static files; there is no SPA build step (design note §7). All mutations are
POST + redirect + GET, so a reload never re-submits a toggle.
"""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from . import APP_VERSION
from .provider import ProviderError
from .runtime import AppRuntime, UnknownModuleError
from .security import (
    CSRF_COOKIE,
    DEFAULT_HEADERS,
    check_origin,
    host_is_loopback,
    new_csrf_token,
    require_csrf,
)

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"

MODULE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

NAV_ITEMS = (
    {"key": "chat", "href": "/chat", "label": "CEO Chat"},
    {"key": "modules", "href": "/modules", "label": "Modules"},
    {"key": "tasks", "href": "/tasks", "label": "Task History"},
    {"key": "settings", "href": "/settings", "label": "Settings"},
)

# Fixed notice vocabulary: query strings never inject free text into a page.
NOTICES: dict[str, dict[str, str]] = {
    "module-enabled": {
        "kind": "ok",
        "text": "Module enabled — the app is starting its process now.",
    },
    "module-disabled": {
        "kind": "ok",
        "text": "Module disabled — the connection was closed and the config updated.",
    },
    "module-checked": {
        "kind": "ok",
        "text": "Health check finished — see the module status below.",
    },
    "module-unknown": {
        "kind": "error",
        "text": "That module is not declared in the registry config.",
    },
    "module-failed": {
        "kind": "error",
        "text": "The module could not be changed — see the status detail below.",
    },
    "provider-saved": {
        "kind": "ok",
        "text": "Provider settings saved. The credential is stored outside git.",
    },
    "provider-cleared": {
        "kind": "ok",
        "text": "Stored credential removed from the local credentials file.",
    },
    "provider-error": {
        "kind": "error",
        "text": "Provider settings were not saved — see the errors on the form.",
    },
}

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _short_ts(value: Any) -> str:
    """Render an ISO timestamp without the microseconds, or a dash."""

    if not isinstance(value, str) or not value:
        return "—"
    return value[:19].replace("T", " ")


templates.env.filters["short_ts"] = _short_ts


class LoopbackBoundary(BaseHTTPMiddleware):
    """Refuse non-loopback ``Host`` values and cross-site origins.

    Runs outside the router so a DNS-rebinding request is rejected before any
    handler touches the registry. The CSRF token is enforced separately as a
    per-route dependency (``require_csrf``).
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not host_is_loopback(request.headers.get("host")):
            return JSONResponse(
                {
                    "detail": (
                        "SoloCorp App only answers loopback Host headers "
                        "(127.0.0.1, localhost, ::1)."
                    )
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            check_origin(request)
        except Exception:  # noqa: BLE001 - converted to an explicit 403 below
            return JSONResponse(
                {"detail": "cross-origin request refused"},
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Issue the token before the handler renders, so the first page load
        # already carries a usable hidden field (the cookie is only stored by
        # the browser once this response returns).
        existing_token = request.cookies.get(CSRF_COOKIE)
        token = existing_token or new_csrf_token()
        request.state.csrf_token = token

        response = await call_next(request)
        for name, value in DEFAULT_HEADERS.items():
            response.headers.setdefault(name, value)
        if existing_token != token:
            response.set_cookie(
                CSRF_COOKIE,
                token,
                httponly=True,
                samesite="strict",
                path="/",
            )
        return response


def create_app(
    runtime: AppRuntime | None = None,
    *,
    install_lifespan: bool = True,
    static_dir: Path | None = None,
) -> FastAPI:
    """Build the app. The app owns the runtime it is given.

    ``install_lifespan=False`` is for tests that drive the runtime themselves;
    the default lifespan starts the health poller and closes every module
    connection on shutdown.
    """

    app_runtime = runtime or AppRuntime()

    lifespan = None
    if install_lifespan:

        @asynccontextmanager
        async def lifespan(_app: FastAPI):
            app_runtime.start()
            try:
                yield
            finally:
                app_runtime.close()

    app = FastAPI(
        title="SoloCorp App",
        version=APP_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.runtime = app_runtime
    app.add_middleware(LoopbackBoundary)
    app.mount(
        "/static",
        StaticFiles(directory=str(static_dir or STATIC_DIR)),
        name="static",
    )

    _register_routes(app, app_runtime)
    return app


def _base_context(request: Request, active_page: str) -> dict[str, Any]:
    return {
        "request": request,
        "active_page": active_page,
        "nav": NAV_ITEMS,
        "app_version": APP_VERSION,
        "csrf_token": getattr(request.state, "csrf_token", "")
        or request.cookies.get(CSRF_COOKIE, ""),
    }


def _notice(request: Request) -> dict[str, str] | None:
    code = request.query_params.get("notice", "")
    return NOTICES.get(code)


def _render(
    request: Request,
    template: str,
    *,
    active_page: str,
    extra: dict[str, Any] | None = None,
    status_code: int = 200,
):
    context = _base_context(request, active_page)
    context["notice"] = _notice(request)
    context.update(extra or {})
    return templates.TemplateResponse(
        request=request,
        name=template,
        context=context,
        status_code=status_code,
    )


def _module_id_or_error(module_id: str) -> str:
    """Reject ids outside the registry's vocabulary before touching any file."""

    if not MODULE_ID_PATTERN.fullmatch(module_id or ""):
        raise UnknownModuleError(module_id)
    return module_id


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


def _register_routes(app: FastAPI, runtime: AppRuntime) -> None:
    reads = APIRouter()
    writes = APIRouter(dependencies=[Depends(require_csrf)])

    # ------------------------------------------------------------- CEO chat

    @reads.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return _redirect("/chat")

    @reads.get("/chat", include_in_schema=False)
    def chat_page(request: Request):
        modules = runtime.modules()
        return _render(
            request,
            "chat.html",
            active_page="chat",
            extra={
                "modules": modules,
                "counts": runtime.counts(),
                "provider": runtime.provider.status(),
            },
        )

    # -------------------------------------------------------------- modules

    @reads.get("/modules", include_in_schema=False)
    def modules_page(request: Request):
        return _render(
            request,
            "modules.html",
            active_page="modules",
            extra={
                "modules": runtime.modules(),
                "counts": runtime.counts(),
                "registry": runtime.registry_health(),
            },
        )

    @writes.post("/modules/{module_id}/toggle", include_in_schema=False)
    async def toggle_module(request: Request, module_id: str):
        try:
            _module_id_or_error(module_id)
        except UnknownModuleError:
            return _redirect("/modules?notice=module-unknown")

        current = runtime.registry.module_config(module_id)
        if current is None:
            return _redirect("/modules?notice=module-unknown")

        enable = current.get("status") != "enabled"
        try:
            runtime.set_enabled(module_id, enable)
        except (UnknownModuleError, ProviderError, OSError, ValueError):
            return _redirect("/modules?notice=module-failed")

        code = "module-enabled" if enable else "module-disabled"
        return _redirect(f"/modules?notice={code}&module={module_id}")

    @writes.post("/modules/{module_id}/check", include_in_schema=False)
    async def check_module(request: Request, module_id: str):
        try:
            _module_id_or_error(module_id)
            runtime.check_health(module_id)
        except (UnknownModuleError, ValueError, OSError):
            return _redirect("/modules?notice=module-failed")
        return _redirect(f"/modules?notice=module-checked&module={module_id}")

    @writes.post("/modules/check-all", include_in_schema=False)
    async def check_all_modules(request: Request):
        runtime.check_all()
        return _redirect("/modules?notice=module-checked")

    @reads.get("/api/modules", include_in_schema=False)
    def api_modules() -> JSONResponse:
        return JSONResponse(
            {
                "modules": runtime.modules(),
                "counts": runtime.counts(),
                "registry": runtime.registry_health(),
            }
        )

    # ---------------------------------------------------------------- tasks

    @reads.get("/tasks", include_in_schema=False)
    def tasks_page(request: Request):
        tasks = runtime.tasks()
        return _render(
            request,
            "tasks.html",
            active_page="tasks",
            extra={"tasks": tasks, "task_count": len(tasks)},
        )

    # ------------------------------------------------------------- settings

    @reads.get("/settings", include_in_schema=False)
    def settings_page(request: Request, notice: str | None = None):
        return _render(
            request,
            "settings.html",
            active_page="settings",
            extra={
                "provider": runtime.provider.status(),
                "form": {"errors": [], "provider": "", "model": "", "base_url": ""},
            },
        )

    @writes.post("/settings/provider", include_in_schema=False)
    async def save_provider(request: Request):
        form = await request.form()
        provider = str(form.get("provider", ""))
        model = str(form.get("model", ""))
        base_url = str(form.get("base_url", ""))
        api_key = str(form.get("api_key", ""))
        api_key_ref = str(form.get("api_key_ref", "") or "")

        try:
            runtime.provider.save(
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
                api_key_ref=api_key_ref or None,
            )
        except ProviderError as exc:
            return _render(
                request,
                "settings.html",
                active_page="settings",
                status_code=status.HTTP_400_BAD_REQUEST,
                extra={
                    "provider": runtime.provider.status(),
                    "form": {
                        "errors": [str(exc)],
                        "provider": provider,
                        "model": model,
                        "base_url": base_url,
                    },
                },
            )
        except OSError as exc:
            return _render(
                request,
                "settings.html",
                active_page="settings",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                extra={
                    "provider": runtime.provider.status(),
                    "form": {
                        "errors": [f"cannot write provider config: {exc}"],
                        "provider": provider,
                        "model": model,
                        "base_url": base_url,
                    },
                },
            )

        return _redirect("/settings?notice=provider-saved")

    @writes.post("/settings/provider/clear-credential", include_in_schema=False)
    async def clear_credential(request: Request):
        settings = runtime.provider.load()
        ref = settings.api_key_ref if settings else None
        runtime.provider.clear_credential(ref)
        return _redirect("/settings?notice=provider-cleared")

    # ---------------------------------------------------------------- health

    @reads.get("/healthz", include_in_schema=False)
    def healthz() -> JSONResponse:
        provider = runtime.provider.status()
        registry = runtime.registry_health()
        payload = {
            "status": "ok" if registry["valid"] else "degraded",
            "app_version": APP_VERSION,
            "provider_state": provider["state"],
            "registry_valid": registry["valid"],
            "modules": runtime.counts(),
        }
        return JSONResponse(payload, status_code=status.HTTP_200_OK)

    app.include_router(reads)
    app.include_router(writes)

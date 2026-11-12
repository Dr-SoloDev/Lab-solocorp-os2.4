"""Loopback request boundary for the local app.

Three independent guards, in order of strength (design note §7):

1. **Loopback binding** — the process listens on ``127.0.0.1`` only. This is the
   primary control; everything below is defence in depth.
2. **Host allowlist** — a request whose ``Host`` header names something other
   than loopback is refused (DNS-rebinding protection).
3. **CSRF token** — every mutating request must echo a per-browser token from
   the ``solocorp_csrf`` cookie in either the ``X-CSRF-Token`` header or the
   form's ``csrf_token`` field. The token, not the ``Origin`` header, is the
   gate; ``Origin`` is only compared when the browser sends one.

MVP is single-user with no account login, so there is no session or password.
"""

from __future__ import annotations

import hmac
import secrets
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, status

CSRF_COOKIE = "solocorp_csrf"
CSRF_FIELD = "csrf_token"
CSRF_HEADER = "x-csrf-token"

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
LOOPBACK_HOSTNAMES = frozenset({"127.0.0.1", "localhost", "::1"})
FORM_CONTENT_TYPES = (
    "application/x-www-form-urlencoded",
    "multipart/form-data",
)

DEFAULT_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    # No inline script or style: the shell ships its own /static files so the
    # policy needs no 'unsafe-inline' exemption.
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; "
        "style-src 'self'; script-src 'self'; frame-ancestors 'none'"
    ),
}


def new_csrf_token() -> str:
    """Generate a token; 32 bytes of urlsafe randomness is plenty for one user."""

    return secrets.token_urlsafe(32)


def split_host(host_header: str | None) -> tuple[str, str | None]:
    """Split ``host[:port]`` into ``(hostname, port)``; IPv6 brackets handled.

    Returns ``("", None)`` for anything unparseable so callers can refuse it
    with one branch instead of nesting.
    """

    if not host_header:
        return "", None
    value = host_header.strip()
    if not value:
        return "", None
    if value.startswith("["):
        closing = value.find("]")
        if closing == -1:
            return "", None
        hostname = value[1:closing]
        rest = value[closing + 1 :]
        if not rest:
            return hostname.lower(), None
        if not rest.startswith(":"):
            return "", None
        return hostname.lower(), rest[1:]
    if value.count(":") == 1:
        hostname, _, port = value.partition(":")
        return hostname.lower(), port
    if ":" in value:
        # Bare IPv6 without brackets and without a port.
        return value.lower(), None
    return value.lower(), None


def host_is_loopback(host_header: str | None) -> bool:
    """True when the ``Host`` header names this machine's loopback interface."""

    hostname, _port = split_host(host_header)
    return hostname in LOOPBACK_HOSTNAMES


def origin_matches(
    origin: str | None, host_header: str | None, sec_fetch_site: str | None = None
) -> bool:
    """Compare the browser's origin assertions against the request ``Host``.

    A missing ``Origin`` is not a failure: non-browser clients and ``curl`` do
    not send one, and the CSRF token still gates the request.

    ``Origin: null`` is an opaque origin, not a same-origin claim. Chromium
    (including the OpenCode desktop browser, verified 2026-11-12) sends exactly
    that header for a same-origin form POST, together with
    ``Sec-Fetch-Site: same-origin``. So ``null`` is accepted only when the
    browser separately asserts same-origin; a cross-site attacker gets
    ``Sec-Fetch-Site: cross-site`` and is refused. This check is defence in
    depth either way — the real gate is the CSRF token in a ``SameSite=strict``
    cookie, which a cross-site POST never carries.
    """

    if not origin:
        return True

    if origin.strip().lower() == "null":
        return (sec_fetch_site or "").strip().lower() == "same-origin"

    try:
        parts = urlsplit(origin)
    except ValueError:
        return False
    if parts.scheme not in ("http", "https"):
        return False
    return parts.netloc.lower() == (host_header or "").strip().lower()


def tokens_match(cookie_token: str | None, supplied: str | None) -> bool:
    """Constant-time comparison that treats an empty value as missing."""

    if not cookie_token or not supplied:
        return False
    return hmac.compare_digest(cookie_token, supplied)


async def require_csrf(request: Request) -> None:
    """FastAPI dependency: reject a mutating request without a valid token.

    The form body is parsed only for form content types and only when the
    header is absent. Starlette caches the parsed form on the request object,
    so the endpoint's own ``await request.form()`` reuses it instead of
    reading a consumed stream.
    """

    if request.method not in MUTATING_METHODS:
        return

    supplied = request.headers.get(CSRF_HEADER)
    if not supplied:
        content_type = request.headers.get("content-type", "")
        if content_type.startswith(FORM_CONTENT_TYPES):
            form = await request.form()
            value = form.get(CSRF_FIELD)
            supplied = value if isinstance(value, str) else None

    if not tokens_match(request.cookies.get(CSRF_COOKIE), supplied):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=("CSRF token missing or invalid — reload the page and try again."),
        )


def check_origin(request: Request) -> None:
    """Reject a mutating request whose origin assertions contradict ``Host``."""

    if request.method not in MUTATING_METHODS:
        return
    if not origin_matches(
        request.headers.get("origin"),
        request.headers.get("host"),
        request.headers.get("sec-fetch-site"),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cross-origin request refused",
        )

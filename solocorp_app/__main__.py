"""Entry point for the local app: ``python -m solocorp_app``.

The server binds loopback only and fails fast. If the port is taken the process
exits with a clear message instead of picking another port silently (design
note §7) — a random port would leave the user staring at a URL that cannot
work.
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
from typing import Mapping, Sequence

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766

# Binding anything wider than loopback would expose a single-user app with no
# login to the network. It is refused rather than warned about.
ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

EXIT_PORT_UNAVAILABLE = 2
EXIT_BAD_CONFIG = 3


class PortUnavailableError(RuntimeError):
    """The requested loopback port is already in use."""


def resolve_binding(
    env: Mapping[str, str] | None = None, argv: Sequence[str] | None = None
) -> tuple[str, int]:
    """Resolve host/port from args then env then defaults.

    Raises ``ValueError`` with an actionable message; ``main`` turns that into a
    non-zero exit instead of a traceback.
    """

    env = os.environ if env is None else env
    parser = argparse.ArgumentParser(
        prog="python -m solocorp_app",
        description="Run the local SoloCorp App shell (loopback only).",
    )
    parser.add_argument(
        "--host",
        default=env.get("SOLOCORP_APP_HOST", DEFAULT_HOST),
        help=f"loopback host to bind (default {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        default=env.get("SOLOCORP_APP_PORT", str(DEFAULT_PORT)),
        help=f"port to bind (default {DEFAULT_PORT})",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    host = str(args.host).strip()
    if host not in ALLOWED_HOSTS:
        raise ValueError(
            f"refusing to bind {host!r}: the app is loopback-only "
            f"(allowed: {', '.join(sorted(ALLOWED_HOSTS))})"
        )

    raw_port = str(args.port).strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError(f"port must be an integer, got {raw_port!r}") from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"port must be between 1 and 65535, got {port}")

    return host, port


def bind_socket(host: str, port: int) -> socket.socket:
    """Bind a listening socket now, so a busy port fails before app startup."""

    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError as exc:
        sock.close()
        raise PortUnavailableError(
            f"cannot bind {host}:{port} ({exc.strerror or exc}). "
            "Stop the process using that port or set SOLOCORP_APP_PORT to a free port."
        ) from exc
    sock.set_inheritable(True)
    return sock


def run(host: str, port: int, sock: socket.socket | None = None) -> int:
    """Run uvicorn on the already-bound socket."""

    import uvicorn

    from .app import create_app

    listener = sock or bind_socket(host, port)
    app = create_app()
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=os.environ.get("SOLOCORP_APP_LOG_LEVEL", "info"),
        lifespan="on",
    )
    server = uvicorn.Server(config)
    print(f"SoloCorp App on http://{host}:{port}  (loopback only)", flush=True)
    try:
        server.run(sockets=[listener])
    except KeyboardInterrupt:  # pragma: no cover - interactive interrupt
        return 0
    finally:
        try:
            listener.close()
        except OSError:  # pragma: no cover - already closed
            pass
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        host, port = resolve_binding(argv=argv)
        sock = bind_socket(host, port)
    except PortUnavailableError as exc:
        print(f"SoloCorp App cannot start: {exc}", file=sys.stderr)
        return EXIT_PORT_UNAVAILABLE
    except ValueError as exc:
        print(f"SoloCorp App cannot start: {exc}", file=sys.stderr)
        return EXIT_BAD_CONFIG

    return run(host, port, sock)


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())

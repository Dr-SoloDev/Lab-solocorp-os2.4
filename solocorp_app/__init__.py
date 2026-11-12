"""SoloCorp App — local-first web shell (PRD Phase 1).

Single process: FastAPI serves the server-rendered UI, the app API and owns the
MCP module connections. Design baseline is
``docs/plans/SOLOCORP-APP-LOCAL-RUNTIME-DESIGN-v0.1.md`` (D1 single process,
D5 explicit provider config, §7 loopback + Jinja defaults).

Phase 1 scope is deliberately narrow: a user can configure one provider/model
and enable/disable a department module from the UI. The CEO loop and the
tracked task path are Phase 2 and are **not** implemented here.
"""

from __future__ import annotations

APP_VERSION = "0.1.0"

__all__ = ["APP_VERSION"]

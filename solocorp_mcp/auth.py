"""
SoloCorp MCP Server — Access Control

3-tier scope:
  - public (level 1): ไม่ต้องใช้ key — list, commands, routing summary
  - team   (level 2): ต้องมี key scope >= team — SOUL.md, search, routing detail
  - admin  (level 3): ต้องมี key scope >= admin — reserved for future admin tools
"""

from __future__ import annotations

import os
import re
import functools

SCOPE_LEVELS = {"public": 1, "team": 2, "admin": 3}

# Pattern: sk-solocorp-{scope}-{random_hex}
KEY_PATTERN = re.compile(r"^sk-solocorp-(public|team|admin)-(.+)$")


def parse_api_key(key: str) -> tuple[str, str] | None:
    """Return (scope, key_id) or None if invalid format."""
    m = KEY_PATTERN.match(key.strip())
    if m:
        return m.group(1), m.group(2)
    return None


def verify_scope(required: str, key: str | None) -> bool:
    """Check if key has at least 'required' scope level.

    - public = ถ้าไม่มี key ก็ผ่าน (default public access)
    - team/admin = ต้องมี key ที่ scope >= level นั้น
    """
    level_required = SCOPE_LEVELS.get(required, 0)

    if key is None:
        # No key provided → only public tools are accessible
        return level_required <= SCOPE_LEVELS["public"]

    parsed = parse_api_key(key)
    if not parsed:
        return False  # Invalid key format

    scope, _ = parsed
    level_granted = SCOPE_LEVELS.get(scope, 0)

    return level_granted >= level_required


def require_scope(level: str):
    """Decorator: gate an MCP tool behind a scope level.

    Usage:
        @mcp.tool()
        @require_scope("team")
        def solocorp_get_department(...):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = os.environ.get("SOLOCORP_API_KEY")
            if not verify_scope(level, key):
                raise PermissionError(
                    f"Requires scope '{level}' — set SOLOCORP_API_KEY with scope >= '{level}'"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator

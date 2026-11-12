"""Phase 2 CEO loop helpers: pure router, timeout budget, error mapping.

Pure by design (R1/R2): no ``axis_mcp.departments.*``, no content engine,
no Concat/ffmpeg, no FastAPI, no busd. Only stdlib. All I/O lives in
``solocorp_app.runtime`` which calls these helpers.
"""

from __future__ import annotations

from typing import Any

BRIEF_MAX_CHARS = 2000

CEO_TURN_BUDGET_S = 180.0

TOOL_TIMEOUTS: dict[str, float] = {
    "default": 60.0,
    "render_*": 150.0,
    "tools/list": 5.0,
}

_GENERIC_CAPABILITIES = frozenset({"tools", "resources"})


def validate_brief(brief: Any) -> str:
    """Trim and validate a CEO brief; raise ValueError when unusable."""

    if not isinstance(brief, str):
        raise ValueError("brief must be 1-2000 characters")
    trimmed = brief.strip()
    if not trimmed or len(trimmed) > BRIEF_MAX_CHARS:
        raise ValueError("brief must be 1-2000 characters")
    return trimmed


def timeout_for_tool(tool_name: str, budget_remaining: float | None = None) -> float:
    """Per-tool ceiling, capped by the remaining turn budget."""

    if tool_name == "tools/list":
        ceiling = TOOL_TIMEOUTS["tools/list"]
    elif tool_name.startswith("render_"):
        ceiling = TOOL_TIMEOUTS["render_*"]
    else:
        ceiling = TOOL_TIMEOUTS["default"]
    if budget_remaining is None:
        return ceiling
    try:
        remaining = float(budget_remaining)
    except (TypeError, ValueError):
        return ceiling
    if remaining <= 0:
        return min(ceiling, 1.0)
    return min(ceiling, remaining)


def route_brief(
    brief: str, modules_view: list[dict[str, Any]]
) -> tuple[str, str, dict[str, Any], str]:
    """Deterministic Phase 2 route: single candidate ``content-creator``.

    Pure (no I/O): reads only ``modules_view`` (``runtime.modules()``).
    Never reroutes silently (R4): when content-creator is not usable the
    caller still gets ``content-creator`` back with a ``no enabled...``
    reason so the turn ends as ``failed`` with a hint, not a silent hop.
    """

    trimmed = brief.strip() if isinstance(brief, str) else ""
    entry: dict[str, Any] | None = None
    for module in modules_view or []:
        if isinstance(module, dict) and module.get("id") == "content-creator":
            entry = module
            break

    tool_name = "content_department_info"
    if entry is not None:
        capabilities = entry.get("capabilities")
        if isinstance(capabilities, list):
            candidates = [
                cap
                for cap in capabilities
                if isinstance(cap, str)
                and cap.strip()
                and cap not in _GENERIC_CAPABILITIES
            ]
            if candidates:
                tool_name = candidates[0]

    args: dict[str, Any] = {"brief": trimmed}

    if entry is None:
        reason = "no enabled department available; content-creator is missing"
    elif not entry.get("enabled"):
        reason = "no enabled department available; content-creator is disabled"
    else:
        observation = entry.get("observation")
        if observation == "error":
            reason = "no enabled department available; content-creator is error"
        elif observation in ("connected", "connecting", None):
            reason = (
                "Phase2 single-candidate route: brief asks for content work; "
                "content-creator is the only enabled department"
            )
        else:
            state = observation or "disconnected"
            reason = f"no enabled department available; content-creator is {state}"

    if len(reason) > 500:
        reason = reason[:500]
    return ("content-creator", tool_name, args, reason)


def artifact_refs_from_result(result: Any) -> list[str]:
    """Extract artifact refs from a tool result; empty when nothing usable."""

    if result is None:
        return []
    if isinstance(result, dict):
        refs = result.get("artifact_refs")
        if isinstance(refs, list) and all(isinstance(item, str) for item in refs):
            return [item for item in refs if item][:20]
        for key in ("filenames", "artifacts"):
            value = result.get(key)
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                return [item for item in value if item][:20]
        for key in ("filename", "result_ref", "artifact", "path", "manifest"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return [value.strip()]
        return []
    if isinstance(result, list):
        strings = [item for item in result if isinstance(item, str) and item.strip()]
        return strings[:20]
    if isinstance(result, str) and result.strip():
        return [result.strip()[:500]]
    return []


def map_error(
    exc: BaseException,
    module_id: str = "content-creator",
    observation: str | None = None,
) -> dict[str, str]:
    """Map any turn failure to the PRD §2.4 vocabulary (6 codes only)."""

    name = type(exc).__name__
    detail = str(exc).strip().replace("\n", " ") if str(exc) else name
    low = detail.lower()
    prefix = module_id or "content-creator"

    if "brief must be 1-2000" in low or "brief must be 1" in low:
        return {
            "code": "BRIEF_INVALID",
            "message": "brief must be 1-2000 characters",
            "hint": "พิมพ์ brief 1–2000 ตัวอักษรแล้วส่งใหม่",
        }
    if "disabled" in low or "is disabled" in low:
        return {
            "code": "MODULE_DISABLED",
            "message": f"{prefix} is disabled",
            "hint": "ไปที่ Modules → Enable content-creator แล้วส่ง brief ใหม่อีกครั้ง",
        }
    if (
        "not connected" in low
        or "is not connected" in low
        or "not-connected" in low
        or "no enabled module" in low
        or "no enabled department" in low
        or "no_route" in low
        or "no route" in low
    ):
        state = observation or "disconnected"
        message = f"{prefix} is not connected ({state})"
        return {
            "code": "MODULE_DISCONNECTED",
            "message": message[:200],
            "hint": "ไปที่ Modules → กด Check ที่ content-creator; ถ้ายัง error ดู last_error ในหน้า Modules",
        }
    if "provider" in low or "unconfigured" in low:
        return {
            "code": "INTERNAL",
            "message": f"internal error: {name}"[:200],
            "hint": "ไปที่ Settings ตั้งค่า provider แล้วส่ง brief ใหม่อีกครั้ง",
        }
    if (
        "timed out" in low
        or "timeout" in low
        or "timedout" in low
        or "exited" in low
        or "malformed" in low
        or "non-object result" in low
    ):
        if observation in ("connected", "connecting", None) and (
            "timed out" in low or "timeout" in low
        ):
            # Timeout during an established call -> tool failure path.
            return {
                "code": "TOOL_FAILED",
                "message": f"content tool failed: {detail[:120]}",
                "hint": "ลอง brief ใหม่อีกครั้ง; ถ้ายังล้มให้ย่อ brief ให้สั้นลงแล้วส่งใหม่",
            }
        return {
            "code": "MODULE_ERROR",
            "message": f"{prefix} unavailable: {detail[:120]}",
            "hint": "ดู last_error ในหน้า Modules แล้วกด Check อีกครั้ง; ถ้ายังล้มให้เก็บ log มาส่ง feedback",
        }
    if (
        "unavailable" in low
        or "connect" in low
        or "handshake" in low
        or "no command" in low
        or "invalid tools" in low
        or "not found in registry" in low
        or "unknown module" in low
    ):
        return {
            "code": "MODULE_ERROR",
            "message": f"{prefix} unavailable: {detail[:120]}",
            "hint": "ดู last_error ในหน้า Modules แล้วกด Check อีกครั้ง; ถ้ายังล้มให้เก็บ log มาส่ง feedback",
        }
    if observation not in ("connected", "connecting", None) and observation is not None:
        # Call attempted while the observation was already bad.
        return {
            "code": "MODULE_DISCONNECTED",
            "message": f"{prefix} is not connected ({observation})"[:200],
            "hint": "ไปที่ Modules → กด Check ที่ content-creator; ถ้ายัง error ดู last_error ในหน้า Modules",
        }
    return {
        "code": "TOOL_FAILED",
        "message": f"content tool failed: {detail[:120]}",
        "hint": "ลอง brief ใหม่อีกครั้ง; ถ้ายังล้มให้ย่อ brief ให้สั้นลงแล้วส่งใหม่",
    }


__all__ = [
    "BRIEF_MAX_CHARS",
    "CEO_TURN_BUDGET_S",
    "TOOL_TIMEOUTS",
    "artifact_refs_from_result",
    "map_error",
    "route_brief",
    "timeout_for_tool",
    "validate_brief",
]

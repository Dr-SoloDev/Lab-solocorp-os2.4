"""Unified read-only status layer for the AXIS runtime.

One call returns the state of seven sources in the ``axis.status/1`` schema.
Nothing here writes, posts, or talks to anything beyond loopback.
"""

from __future__ import annotations

from .aggregator import (
    CRITICAL_SOURCES,
    SCHEMA,
    SOURCE_IDS,
    TOOL_VERSION,
    WEIGHTS,
    aggregate,
    reset_cache,
    score_sources,
)

__all__ = [
    "CRITICAL_SOURCES",
    "SCHEMA",
    "SOURCE_IDS",
    "TOOL_VERSION",
    "WEIGHTS",
    "aggregate",
    "reset_cache",
    "score_sources",
]

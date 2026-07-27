"""Utility functions."""

from datetime import datetime
from typing import Any


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO string."""
    return dt.isoformat()


def format_output(data: dict) -> str:
    """Format dict output for display."""
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"  {key}:")
            for k, v in value.items():
                lines.append(f"    {k}: {v}")
        else:
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def get_current_time() -> str:
    """Get current time as ISO string."""
    return datetime.now().isoformat()

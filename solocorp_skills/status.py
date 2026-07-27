"""Project and task status checking."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from solocorp_skills.core import SolocorpError, SolocorpClient

BUS_DIR = Path(__file__).parent.parent / "bus"


def check_status(project: str) -> dict:
    """Check status of a project.

    Args:
        project: Project name or ID

    Returns:
        Dict with project status
    """
    client = SolocorpClient()
    if client.is_ready():
        try:
            return client._api_get(f"/v1/projects/{project}")
        except Exception:
            pass

    return _status_local(project)


def project_status(project: str) -> dict:
    """Alias for check_status (backward compatible)."""
    return check_status(project)


def _status_local(project: str) -> dict:
    """Get status from local files."""
    projects_dir = BUS_DIR / "projects"
    project_path = projects_dir / project

    result = {
        "project": project,
        "status": "unknown",
        "progress": 0,
        "found": project_path.exists(),
    }

    if project_path.exists():
        manifest = project_path / "manifest.json"
        if manifest.exists():
            import json
            manifest_data = json.loads(manifest.read_text())
            result.update(manifest_data)

    return result

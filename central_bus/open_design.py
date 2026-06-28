"""
open-design bridge — thin HTTP client to Open Design daemon (port 41551)
Read-only. No write operations.
"""
import json
import urllib.request
from typing import Any

DAEMON_URL = "http://127.0.0.1:41551"

# Tools permitted per department role
DEPT_TOOLS = {
    "design":      {"get_active_context", "list_projects", "get_project", "list_files", "get_artifact", "search_files"},
    "ui_designer": {"get_artifact", "get_file", "search_files"},
    "engineering": {"get_artifact", "get_file", "search_files"},
    "qa":          {"get_artifact", "get_file"},
}


def _call(tool: str, params: dict) -> Any:
    data = json.dumps({"tool": tool, "params": params}).encode()
    req = urllib.request.Request(
        f"{DAEMON_URL}/api/mcp",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def call(dept: str, tool: str, **params) -> Any:
    """Call an open-design tool on behalf of a department.
    Raises PermissionError if tool not in dept's allowed set.
    """
    allowed = DEPT_TOOLS.get(dept, set())
    if tool not in allowed:
        raise PermissionError(f"{dept} cannot use open-design tool '{tool}'")
    return _call(tool, params)


# Convenience wrappers used by each department
def get_active_context() -> dict:
    return _call("get_active_context", {})

def list_projects() -> list:
    return _call("list_projects", {})

def get_artifact(project_id: str, artifact_id: str) -> dict:
    return _call("get_artifact", {"projectId": project_id, "artifactId": artifact_id})

def get_file(project_id: str, path: str) -> str:
    return _call("get_file", {"projectId": project_id, "path": path})

def search_files(project_id: str, query: str) -> list:
    return _call("search_files", {"projectId": project_id, "query": query})

def list_files(project_id: str) -> list:
    return _call("list_files", {"projectId": project_id})

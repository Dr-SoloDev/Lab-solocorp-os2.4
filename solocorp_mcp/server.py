#!/usr/bin/env python3
"""
SoloCorp OS MCP Server — ให้ external coding agents (OpenCode, Kimi CLI, Claude Code, Codex CLI, Cursor ฯลฯ)
เรียกใช้ capabilities ของ SoloCorp OS ผ่าน MCP protocol

Tools ที่ expose:
  - solocorp_list_departments  — ดูรายชื่อแผนกทั้งหมด
  - solocorp_get_department    — อ่าน SOUL.md profile ของแผนก
  - solocorp_route_request     — รู้ว่าควรส่งเรื่องนี้ไปแผนกไหน
  - solocorp_search_profiles   — ค้นหาทั่วทุก SOUL.md
  - solocorp_get_routing_rules — ดู routing rules
  - solocorp_get_commands      — ดู pipeline commands

Resources:
  - solocorp://departments          — รายชื่อแผนก
  - solocorp://departments/{id}     — SOUL.md profile
  - solocorp://routing/rules        — routing rules
  - solocorp://routing/semantic     — semantic routing profiles
  - solocorp://commands             — pipeline commands

Run:
  python3 -m solocorp_mcp.server
  # หรือ register ใน MCP client config:
  # {
  #   "mcpServers": {
  #     "solocorp": {
  #       "command": "python3",
  #       "args": ["-m", "solocorp_mcp.server"]
  #     }
  #   }
  # }
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# ── Paths ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = ROOT / "profiles"
INDEX_PATH = PROFILES_DIR / "INDEX.md"
BUS_SYSTEM_DIR = ROOT / "bus" / "system"
ROUTING_RULES_PATH = BUS_SYSTEM_DIR / "routing_rules.json"
SEMANTIC_PROFILES_PATH = BUS_SYSTEM_DIR / "semantic_profiles.json"
CLAUDE_PATH = ROOT / "CLAUDE.md"


# ── Data Loaders ──────────────────────────────────────────────────────

def load_index() -> list[dict[str, str]]:
    """Parse INDEX.md -> list of {id, name, head, responsibility, status}"""
    if not INDEX_PATH.exists():
        return []
    text = INDEX_PATH.read_text(encoding="utf-8")
    departments = []
    # Match rows in the C-Level / Department Heads tables: | 01-ceo | **CEO** | [name](path) | responsibility | Active |
    pattern = re.compile(
        r"\|\s*`(\d+-\w+)`\s*\|\s*\*\*(\w[^*]+)\*\*\s*\|\s*\[([^\]]+)\]\([^)]+\)\s*\|\s*([^|]+)\s*\|\s*(\w+)",
    )
    for m in pattern.finditer(text):
        departments.append({
            "id": m.group(1),
            "name": m.group(2).strip(),
            "head": m.group(3).strip(),
            "responsibility": m.group(4).strip(),
            "status": m.group(5).strip(),
        })
    return departments


def load_soul_metadata(path: Path) -> dict[str, str]:
    """Read key fields from a SOUL.md file."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    name = re.search(r"\*\*ชื่อ[^\*]*\*\*\s*\|\s*(.+)", text)
    role = re.search(r"\*\*ตำแหน่ง\*\*\s*\|\s*(.+)", text)
    dept = re.search(r"\*\*สังกัด\*\*\s*\|\s*(.+)", text)
    mission = re.search(r"## 2\. Core Mission\n+(.+?)(?=\n##|\Z)", text, re.DOTALL)
    return {
        "name": name.group(1).strip() if name else path.stem,
        "role": role.group(1).strip() if role else "",
        "dept": dept.group(1).strip() if dept else "",
        "mission": mission.group(1).strip()[:500] if mission else "",
        "path": str(path.relative_to(ROOT)),
    }


def load_all_profiles() -> list[dict[str, str]]:
    """Load metadata from every SOUL.md in profiles/ (heads + specialists)."""
    profiles = []
    for soul_file in sorted(PROFILES_DIR.rglob("*.SOUL.md")):
        meta = load_soul_metadata(soul_file)
        if meta:
            profiles.append(meta)
    # Also include non-.SOUL.md SOUL.md files (department heads)
    for dept_dir in sorted(PROFILES_DIR.iterdir()):
        if dept_dir.is_dir():
            soul = dept_dir / "SOUL.md"
            if soul.exists():
                meta = load_soul_metadata(soul)
                if meta and not any(p["path"] == str(soul.relative_to(ROOT)) for p in profiles):
                    profiles.append(meta)
    return profiles


def load_routing_rules() -> list[dict[str, Any]]:
    if ROUTING_RULES_PATH.exists():
        return json.loads(ROUTING_RULES_PATH.read_text()).get("rules", [])
    return []


def load_semantic_profiles() -> dict[str, list[str]]:
    if SEMANTIC_PROFILES_PATH.exists():
        return json.loads(SEMANTIC_PROFILES_PATH.read_text()).get("profiles", {})
    return {}


def load_routing_table_from_claude() -> list[dict[str, str]]:
    """Parse routing table from CLAUDE.md (OpenCode Agent Routing section)."""
    if not CLAUDE_PATH.exists():
        return []
    text = CLAUDE_PATH.read_text(encoding="utf-8")
    routing = []
    pattern = re.compile(r"\|\s*([^|]+)\s*\|\s*`@([^`]+)`\s*\|")
    in_section = False
    for line in text.split("\n"):
        if "OpenCode Agent Routing" in line:
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith("|--") or line.startswith("|:"):
            continue
        if line.startswith("|"):
            m = pattern.search(line)
            if m:
                routing.append({
                    "topic": m.group(1).strip(),
                    "agent": f"@{m.group(2).strip()}",
                })
        if line.strip() == "" and routing:
            continue
        if not line.startswith("|") and routing:
            break
    return routing


def build_commands_list() -> list[dict[str, str]]:
    """Return pipeline commands from CLAUDE.md."""
    if not CLAUDE_PATH.exists():
        return []
    text = CLAUDE_PATH.read_text(encoding="utf-8")
    commands = []
    in_section = False
    header_seen = False
    for line in text.split("\n"):
        if "Pipeline Commands" in line:
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith("|--") or line.startswith("|:"):
            header_seen = True
            continue
        if line.startswith("|") and header_seen:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2 and not parts[0].startswith(":"):
                commands.append({"command": parts[0], "action": parts[1].split("—")[0].strip() if "—" in parts[1] else parts[1]})
        if not line.startswith("|") and commands:
            break
    return commands


# ── MCP Server ───────────────────────────────────────────────────────

def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        print("Need mcp package: pip install mcp", file=sys.stderr)
        sys.exit(1)

    mcp = FastMCP(
        "solocorp-os",
        instructions="""\
SoloCorp OS MCP Server — exposes the SoloCorp organizational OS to external coding agents.

Use this server when you need to:
- Understand SoloCorp's department structure and who owns what
- Route a request to the correct department by topic
- Read department head profiles (SOUL.md) for identity, mission, and rules
- Look up routing rules and pipeline commands
- Search across all agent profiles for capabilities
""",
    )

    # ── Resources ────────────────────────────────────────────────────

    @mcp.resource("solocorp://departments")
    def list_departments_resource() -> str:
        """List all SoloCorp OS departments with ID, name, head, and status."""
        depts = load_index()
        if not depts:
            return "No department index found."
        lines = ["# SoloCorp OS — Departments\n"]
        lines.append(f"| # | Department | Head | Responsibility | Status |")
        lines.append(f"|---|------------|------|----------------|--------|")
        for i, d in enumerate(depts, 1):
            lines.append(f"| {i} | `{d['id']}` | **{d['name']}** | {d['head']} | {d['responsibility']} | {d['status']} |")
        return "\n".join(lines)

    @mcp.resource("solocorp://departments/{dept_id}")
    def get_department_resource(dept_id: str) -> str:
        """Get the full SOUL.md profile for a department (e.g. '01-ceo', '07-engineering')."""
        soul_path = PROFILES_DIR / dept_id / "SOUL.md"
        if soul_path.exists():
            return soul_path.read_text(encoding="utf-8")
        # Try matching by prefix
        for d in sorted(PROFILES_DIR.iterdir()):
            if d.is_dir() and d.name.startswith(dept_id.split("-")[0].zfill(2)):
                soul = d / "SOUL.md"
                if soul.exists():
                    return soul.read_text(encoding="utf-8")
        return f"# Department '{dept_id}' not found.\n\nAvailable: " + ", ".join(
            d.name for d in sorted(PROFILES_DIR.iterdir()) if d.is_dir() and (d / "SOUL.md").exists()
        )

    @mcp.resource("solocorp://routing/rules")
    def routing_rules_resource() -> str:
        """Keyword-based routing rules: trigger keywords → route_to department."""
        rules = load_routing_rules()
        return json.dumps(rules, indent=2, ensure_ascii=False)

    @mcp.resource("solocorp://routing/semantic")
    def semantic_profiles_resource() -> str:
        """Semantic routing profiles with Thai + English phrases per department."""
        profiles = load_semantic_profiles()
        return json.dumps(profiles, indent=2, ensure_ascii=False)

    @mcp.resource("solocorp://commands")
    def commands_resource() -> str:
        """Available pipeline commands for SoloCorp OS."""
        cmds = build_commands_list()
        if not cmds:
            return "No commands found."
        lines = ["# SoloCorp OS — Pipeline Commands\n"]
        lines.append(f"| Command | Action |")
        lines.append(f"|---------|--------|")
        for c in cmds:
            lines.append(f"| `{c['command']}` | {c['action']} |")
        return "\n".join(lines)

    # ── Tools ────────────────────────────────────────────────────────

    @mcp.tool()
    def solocorp_list_departments(status_filter: str | None = None) -> str:
        """List all SoloCorp OS departments.

        Each department has an ID (e.g. '01-ceo'), name (e.g. 'CEO'),
        head name, responsibility description, and status (Active/Design/Planned).

        Args:
            status_filter: Optional filter — 'Active', 'Design', or 'Planned'.
                          Returns all departments if omitted.
        """
        depts = load_index()
        if status_filter:
            depts = [d for d in depts if d["status"].lower() == status_filter.lower()]
        if not depts:
            return "No departments found." if not status_filter else f"No departments with status '{status_filter}'."
        lines = ["# SoloCorp OS — Departments\n"]
        lines.append(f"| ID | Department | Head | Responsibility | Status |")
        lines.append(f"|----|------------|------|----------------|--------|")
        for d in depts:
            lines.append(f"| `{d['id']}` | **{d['name']}** | {d['head']} | {d['responsibility']} | {d['status']} |")
        return "\n".join(lines)

    @mcp.tool()
    def solocorp_get_department(dept_id_or_name: str) -> str:
        """Get the full SOUL.md profile of a department.

        Returns the complete identity, mission, rules, and team structure.

        Args:
            dept_id_or_name: Department ID like '01-ceo', '07-engineering',
                           or partial name like 'ceo', 'engineering', 'cfo'.
        """
        # Direct match
        soul_path = PROFILES_DIR / dept_id_or_name / "SOUL.md"
        if soul_path.exists():
            return soul_path.read_text(encoding="utf-8")

        # Try prefix match (e.g. "01-ceo" from "ceo")
        for d in sorted(PROFILES_DIR.iterdir()):
            if d.is_dir() and (dept_id_or_name in d.name or d.name.startswith(dept_id_or_name)):
                soul = d / "SOUL.md"
                if soul.exists():
                    return soul.read_text(encoding="utf-8")

        return (
            f"Department '{dept_id_or_name}' not found.\n\n"
            f"Try: {', '.join(d.name for d in sorted(PROFILES_DIR.iterdir()) if d.is_dir() and (d / 'SOUL.md').exists())}"
        )

    @mcp.tool()
    def solocorp_route_request(query: str) -> str:
        """Route a natural language request to the correct SoloCorp department.

        Uses keyword-based routing rules and semantic profiles to determine
        which department should handle the request.

        Args:
            query: Natural language description of what you need help with.
                  Examples: 'I need to fix a bug in the login page',
                  'design a new landing page', 'check our monthly budget'
        """
        q_lower = query.lower()

        # 1. Try keyword routing
        rules = load_routing_rules()
        best_match = None
        best_score = 0

        for rule in rules:
            keywords = rule.get("trigger", {}).get("keywords", [])
            score = sum(1 for kw in keywords if kw.lower() in q_lower)
            if score > best_score:
                best_score = score
                best_match = rule

        # 2. Try semantic match
        if best_score == 0:
            semantic = load_semantic_profiles()
            for dept, phrases in semantic.items():
                score = sum(1 for phrase in phrases if phrase.lower() in q_lower)
                if score > best_score:
                    best_score = score
                    best_match = {"route_to": dept, "priority": "normal"}

        # 3. Route from CLAUDE.md routing table
        if best_score == 0:
            routing_table = load_routing_table_from_claude()
            for entry in routing_table:
                topic_words = entry["topic"].lower().split(", ")
                if any(tw in q_lower for tw in topic_words):
                    best_match = {"route_to": entry["agent"], "priority": "normal"}
                    break

        if best_match:
            route_to = best_match.get("route_to", "ceo")
            priority = best_match.get("priority", "normal")
            departments = load_index()
            dept_info = next(
                (d for d in departments if route_to in d["id"] or route_to == d["name"].lower()),
                None,
            )
            result = f"## Route Result\n\n"
            result += f"**Route to:** `@{route_to}`\n"
            result += f"**Priority:** {priority}\n"
            if dept_info:
                result += f"**Department:** {dept_info['name']} ({dept_info['head']})\n"
                result += f"**Responsibility:** {dept_info['responsibility']}\n"
                result += f"**Status:** {dept_info['status']}\n"
            result += f"\n**Query:** {query}\n"
            return result

        return f"## Route Result\n\n**Route to:** `@ceo-turbo` (fallback — ไม่มี match ชัดเจน)\n**Query:** {query}\n\nℹ️ ไม่พบ department ที่ match โดยตรง — ส่ง CEO เพื่อพิจารณา"

    @mcp.tool()
    def solocorp_search_profiles(keyword: str) -> str:
        """Search across all SOUL.md profiles in SoloCorp OS.

        Searches department head profiles and specialist agent profiles
        for matching keywords in names, roles, and missions.

        Args:
            keyword: Search term (Thai or English). Matches against name,
                    role, department, and mission fields.
        """
        kw = keyword.lower()
        profiles = load_all_profiles()
        matches = []
        for p in profiles:
            if (kw in p.get("name", "").lower() or
                kw in p.get("role", "").lower() or
                kw in p.get("dept", "").lower() or
                kw in p.get("mission", "").lower()):
                matches.append(p)

        if not matches:
            return f"No profiles match '{keyword}'."

        lines = [f"# Search Results: '{keyword}'\n"]
        lines.append(f"| Name | Role | Department | File |")
        lines.append(f"|------|------|------------|------|")
        for m in matches:
            lines.append(f"| {m.get('name', '?')} | {m.get('role', '?')} | {m.get('dept', '?')} | `{m.get('path', '?')}` |")
        return "\n".join(lines)

    @mcp.tool()
    def solocorp_get_routing_rules() -> str:
        """Get the keyword-based routing rules used by SoloCorp OS.

        Each rule maps trigger keywords to a destination department
        with a priority level (critical/high/normal).
        """
        rules = load_routing_rules()
        if not rules:
            return "No routing rules found."
        lines = ["# SoloCorp OS — Routing Rules\n"]
        lines.append(f"| Rule ID | Keywords | Route To | Priority |")
        lines.append(f"|---------|----------|----------|----------|")
        for r in rules:
            keywords = ", ".join(r.get("trigger", {}).get("keywords", []))
            route_to = r.get("route_to", "?")
            priority = r.get("priority", "normal")
            lines.append(f"| `{r.get('rule_id', '?')}` | {keywords} | `@{route_to}` | {priority} |")
        return "\n".join(lines)

    @mcp.tool()
    def solocorp_get_commands() -> str:
        """List all available pipeline commands in SoloCorp OS.

        These slash-commands can be used within OpenCode to run
        pipelines, handoffs, audits, and deployments.
        """
        cmds = build_commands_list()
        if not cmds:
            return "No commands found."
        lines = ["# SoloCorp OS — Pipeline Commands\n"]
        lines.append(f"| Command | Action |")
        lines.append(f"|---------|--------|")
        for c in cmds:
            lines.append(f"| `{c['command']}` | {c['action']} |")
        return "\n".join(lines)

    @mcp.tool()
    def solocorp_get_team_members(dept_id: str) -> str:
        """List specialist team members under a department.

        Shows all specialist agents (SOUL.md files) under a department head,
        including their role and responsibilities.

        Args:
            dept_id: Department ID like '01-ceo', '07-engineering', '16-neteng'.
        """
        dept_dir = PROFILES_DIR / dept_id
        if not dept_dir.exists() or not dept_dir.is_dir():
            return f"Department '{dept_id}' not found."

        # Find team directory (head/team/ or head/head/team/)
        team_dirs = list(dept_dir.rglob("team"))
        if not team_dirs:
            return f"No specialist team found for '{dept_id}'. (Department heads often work alone.)"

        specialist_souls = []
        for td in team_dirs:
            for f in sorted(td.glob("*.SOUL.md")):
                meta = load_soul_metadata(f)
                if meta:
                    specialist_souls.append(meta)

        if not specialist_souls:
            return f"No specialist agents defined for '{dept_id}'."

        lines = [f"# Team: {dept_id}\n"]
        lines.append(f"| # | Specialist | Role | Department |")
        lines.append(f"|---|------------|------|------------|")
        for i, s in enumerate(specialist_souls, 1):
            lines.append(f"| {i} | **{s.get('name', '?')}** | {s.get('role', '?')} | {s.get('dept', '?')} |")
        return "\n".join(lines)

    return mcp


# ── Entrypoint ────────────────────────────────────────────────────────

def main():
    mcp = create_server()
    mcp.run()


if __name__ == "__main__":
    main()

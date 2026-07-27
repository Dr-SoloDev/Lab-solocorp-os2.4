"""Department management and lookup."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from solocorp_skills.core import PROFILES_DIR


def get_department(dept_name: str) -> dict:
    """Get department info from profile.

    Args:
        dept_name: Department name (e.g., "engineering", "design", "ceo")
                   Supports both plain names and prefixed names (01-ceo, 07-engineering)

    Returns:
        Dict with department info, or None if not found
    """
    # Try loading from Central Bus first
    try:
        from solocorp_skills.core import SolocorpClient
        client = SolocorpClient()
        if client.is_ready():
            result = client._api_get(f"/v1/departments/{dept_name}")
            if result:
                return result
    except Exception:
        pass

    # Fall back to local profile
    # Try both plain name and prefixed name
    profile_path = PROFILES_DIR / dept_name
    if not profile_path.exists():
        # Try with common prefixes
        for prefix in ["01-", "02-", "03-", "04-", "05-", "06-", "07-", "08-", "09-", "10-", "11-", "12-", "13-", "14-", "15-", "16-", "17-", "18-", "19-"]:
            candidate = prefix + dept_name
            candidate_path = PROFILES_DIR / candidate
            if candidate_path.exists():
                profile_path = candidate_path
                break
        else:
            return None

    soul_path = profile_path / "SOUL.md"
    if soul_path.exists():
        content = soul_path.read_text(encoding="utf-8")
        # Parse basic info from SOUL.md
        return _parse_soul(content, dept_name)

    return None


def list_departments() -> list[dict]:
    """List all departments.

    Returns:
        List of department names and basic info
    """
    departments = []
    for d in sorted(PROFILES_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            soul_path = d / "SOUL.md"
            if soul_path.exists():
                content = soul_path.read_text(encoding="utf-8")
                dept_info = _parse_soul(content, d.name)
                departments.append(dept_info)
    return departments


def _parse_soul(content: str, name: str) -> dict:
    """Parse basic info from SOUL.md content."""
    import re
    info = {"name": name}

    def clean(val):
        """Clean markdown artifacts from value."""
        if not val:
            return val
        val = re.sub(r"\*\*", "", val)
        val = re.sub(r"\`", "", val)
        val = val.strip()
        return val

    # Pattern 1: Bullet points (from agent files)
    bullet_patterns = [
        (r"- \*\*ชื่อ(?:เล่น)?\*\*[：:]\s*(.+?)(?:\n|$)", "name_thai"),
        (r"- \*\*ชื่อ\*\*[：:]\s*(.+?)(?:\n|$)", "name_thai"),
        (r"- \*\*บทบาท\*\*[：:]\s*(.+?)(?:\n|$)", "role"),
        (r"- \*\*Role\*\*[：:]\s*(.+?)(?:\n|$)", "role"),
        (r"- \*\*Model\*\*[：:]\s*(.+?)(?:\n|$)", "model"),
        (r"- \*\*ตำแหน่ง\*\*[：:]\s*(.+?)(?:\n|$)", "role"),
    ]

    for pattern, field in bullet_patterns:
        match = re.search(pattern, content)
        if match:
            info[field] = clean(match.group(1).strip())
            break

    # Pattern 2: Table format (from SOUL.md)
    table_blocks = re.findall(
        r"\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]+)\s*\|",
        content
    )
    for label, value in table_blocks:
        label = label.strip()
        value = value.strip()
        if label in ("ชื่อ", "ชื่อเล่น"):
            info["name_thai"] = clean(value)
        elif label in ("ตำแหน่ง", "Role"):
            info["role"] = clean(value)
        elif label == "Model":
            info["model"] = clean(value)

    # Pattern 3: Generic "ชื่อ:" anywhere in content
    if "name_thai" not in info:
        name_match = re.search(r"(?:ชื่อ(?:เล่น)?|Name)\s*[：:]\s*(.+?)(?:\n|$)", content)
        if name_match:
            info["name_thai"] = clean(name_match.group(1))

    if "role" not in info:
        role_match = re.search(r"(?:ตำแหน่ง|Role)\s*[：:]\s*(.+?)(?:\n|$)", content)
        if role_match:
            info["role"] = clean(role_match.group(1))

    if "model" not in info:
        model_match = re.search(r"Model\s*[：:]\s*(.+?)(?:\n|$)", content)
        if model_match:
            info["model"] = clean(model_match.group(1))

    return info

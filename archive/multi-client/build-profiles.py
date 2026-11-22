#!/usr/bin/env python3
"""Build adapter profiles for multiple AI clients from SOUL.md source files."""

import os
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
PROFILES = ROOT / "profiles"
DIST = ROOT / "dist"

CLIENTS = ["droid", "codex", "hermes"]


def find_soul_files():
    """Find all SOUL.md files (head + team)."""
    return sorted(PROFILES.rglob("*.SOUL.md")) + sorted(
        p for p in PROFILES.rglob("SOUL.md") if p.parent.name != "profiles"
    )


def extract_identity(content: str) -> dict:
    """Extract key fields from SOUL.md."""
    name = re.search(r"#.*?—\s*(.+)", content)
    role = re.search(r"\*\*ตำแหน่ง\*\*\s*\|\s*(.+)", content)
    dept = re.search(r"\*\*สังกัด\*\*\s*\|\s*(.+)", content)
    mission_block = re.search(r"## 2\. Core Mission\n+(.+?)(?=\n##|\Z)", content, re.DOTALL)

    return {
        "name": name.group(1).strip() if name else "Agent",
        "role": role.group(1).strip() if role else "",
        "dept": dept.group(1).strip() if dept else "",
        "mission": mission_block.group(1).strip()[:500] if mission_block else "",
    }


def build_droid(soul_path: Path, content: str, meta: dict) -> str:
    """Claude Code / Kiro format — loads full SOUL.md via @reference."""
    rel = soul_path.relative_to(ROOT)
    return f"""# Agent: {meta['name']}

@{rel}

## Instructions
- ทำงานตาม Identity และ Responsibilities ที่กำหนดใน SOUL.md ด้านบน
- ห้ามออกนอกขอบเขตที่ระบุใน "สิ่งที่ไม่ทำ"
- ภาษาไทยเป็นหลัก ยกเว้น technical terms
"""


def build_codex(soul_path: Path, content: str, meta: dict) -> str:
    """OpenAI Codex / generic OpenAI-compatible system prompt."""
    # Strip markdown tables/headers for cleaner prompt
    clean = re.sub(r"\|.+\|", "", content)
    clean = re.sub(r"^#+\s+", "", clean, flags=re.MULTILINE)
    clean = re.sub(r"\*\*(.+?)\*\*", r"\1", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return f"""You are {meta['name']}.
Role: {meta['role']}
Department: {meta['dept']}

{clean[:3000]}
"""


def build_hermes(soul_path: Path, content: str, meta: dict) -> str:
    """Hermes-compatible profile — returns SOUL.md as-is (native format)."""
    return content


BUILDERS = {
    "droid": (build_droid, "CLAUDE.md"),
    "codex": (build_codex, "system_prompt.md"),
    "hermes": (build_hermes, "SOUL.md"),
}


def profile_key(soul_path: Path) -> str:
    """Create a stable output path key from SOUL.md location."""
    key = str(soul_path.relative_to(PROFILES))
    if key.endswith("/SOUL.md") or key == "SOUL.md":
        key = key[: -len("SOUL.md")] + "head"
    elif key.endswith(".SOUL.md"):
        key = key[: -len(".SOUL.md")]
    return key.rstrip("/")


def main():
    souls = find_soul_files()
    print(f"Found {len(souls)} SOUL.md files")

    for client in CLIENTS:
        builder_fn, out_name = BUILDERS[client]
        for soul_path in souls:
            content = soul_path.read_text(encoding="utf-8")
            meta = extract_identity(content)
            key = profile_key(soul_path)

            out_dir = DIST / client / key
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / out_name
            out_file.write_text(builder_fn(soul_path, content, meta), encoding="utf-8")

        print(f"[{client}] {len(souls)} profiles → dist/{client}/")

    print("Done.")


if __name__ == "__main__":
    main()

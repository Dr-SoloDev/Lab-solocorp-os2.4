#!/usr/bin/env python3
"""Generate docs/SPECIALIST-MANIFEST-v1.0.md from the real repository roster.

Sources of truth (read from disk, never hand-maintained in the document):
  - profiles/*/SOUL.md                  -> Department Heads (20)
  - profiles/**/team/*.SOUL.md          -> specialist roles (67)
  - .opencode/agents/*.md               -> agent runtime files (87)

Constraints:
  - Python standard library only
  - deterministic output: no timestamps, no commit hashes, sorted by dept then slug
  - no network access

Usage:
    python3 scripts/generate-specialist-manifest.py

Exit codes:
    0 = manifest written, every mapped source file exists
    1 = at least one mapped source file is missing (document still written with MISSING)
"""

from __future__ import annotations

import glob
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = REPO_ROOT / "profiles"
AGENTS_DIR = REPO_ROOT / ".opencode" / "agents"
OUTPUT_PATH = REPO_ROOT / "docs" / "SPECIALIST-MANIFEST-v1.0.md"

DOC_VERSION = "v1.0.0"
DESCRIPTION_LIMIT = 120

# Frontmatter contract every agent file is expected to carry.
FRONTMATTER_KEYS = ("name", "description", "mode", "agents_md", "color")

# SOUL role (filename stem without the NN- prefix) -> agent slug.
# Only roles whose SOUL stem differs from the agent filename need an override.
ROLE_SLUG_OVERRIDES = {
    "สถาปนิกแบ็กเอนด์": "backend-architect",
    "นักพัฒนาอาวุโส": "senior-developer",
    "สถาปนิกซอฟต์แวร์": "software-architect",
    "exception-triage-agent": "exception-triage",
    "cron-pipeline-agent": "cron-pipeline",
    "lead-researcher": "rd-lab",
}

# Department directory -> head agent slug.
HEAD_AGENT_SLUGS = {
    "01-ceo": "ceo-turbo",
    "02-cfo": "cfo-meetoo",
    "02-coo": "coo-kit",
    "03-cmo": "cmo-mark",
    "04-orchestrator": "orchestrator-wut",
    "05-architect": "architect-songsak",
    "06-product": "product-produck",
    "07-engineering": "engineering-changful",
    "08-design": "design-kreet",
    "09-ui-designer": "ui-designer",
    "10-qa": "qa",
    "11-sales": "sales",
    "12-support": "support",
    "13-legal": "legal-tulya",
    "14-web3": "web3-aywa",
    "15-content-creator": "content-creator-sek",
    "16-neteng": "neteng-neet",
    "17-cybersec": "cybersec-sai",
    "18-psychology": "psych-jit",
    "19-rd-lab": "rd-lab",
}

# Team roles that reuse a head agent file instead of owning a separate agent file.
# `lead-researcher` reports to the R&D Lab head `rd-lab`.
TEAM_HEAD_SHARED_SLUGS = {"rd-lab"}

# Reporting groups; ordering inside each group is dept ascending, then slug.
TRACKS = (
    ("CTO/Technical", ("05-architect", "07-engineering", "16-neteng", "17-cybersec")),
    (
        "CMO/Creative",
        ("03-cmo", "06-product", "08-design", "09-ui-designer", "15-content-creator"),
    ),
    (
        "COO/Operations",
        ("02-coo", "04-orchestrator", "10-qa", "11-sales", "12-support"),
    ),
    (
        "CFO/Governance",
        ("02-cfo", "13-legal", "14-web3", "18-psychology", "19-rd-lab"),
    ),
)

# Head display-name patterns, highest priority first.
HEAD_NAME_PATTERNS = (
    re.compile(r"^\*\*ชื่อเล่น:\*\*\s*(.+?)\s*$", re.M),
    re.compile(r"^\*\*ชื่อ:\*\*\s*(.+?)\s*$", re.M),
    re.compile(r"^\|\s*\*\*ชื่อ\*\*\s*\|\s*(.+?)\s*\|", re.M),
    re.compile(r"^\|\s*\*\*หัวหน้าแล็บ\*\*\s*\|\s*(.+?)\s*\|", re.M),
    re.compile(r"^\|\s*\*\*ชื่อแผนก\*\*\s*\|\s*(.+?)\s*\|", re.M),
)

FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.S)
FRONTMATTER_LINE_RE = re.compile(r"^([A-Za-z_]+):\s*(.*)$")

MISSING = "MISSING"


class RoleRecord:
    """One specialist role: its SOUL file plus the agent file it resolves to."""

    def __init__(self, dept: str, stem: str, soul_path: Path) -> None:
        self.dept = dept
        self.stem = stem
        self.soul_path = soul_path
        role = re.sub(r"^\d+-", "", stem)
        self.slug = ROLE_SLUG_OVERRIDES.get(role, role)
        self.frontmatter: dict[str, str] = {}
        self.agent_path = AGENTS_DIR / f"{self.slug}.md"

    @property
    def rel_soul(self) -> str:
        return self.soul_path.relative_to(REPO_ROOT).as_posix()


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as handle:
        return handle.read()


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the flat key/value pairs of a YAML-style agent frontmatter block."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line or line[0].isspace():
            continue
        item = FRONTMATTER_LINE_RE.match(line)
        if not item:
            continue
        key, value = item.group(1), item.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key] = value
    return data


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def code(value: str) -> str:
    return f"`{value}`"


def truncate(value: str, limit: int = DESCRIPTION_LIMIT) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def extract_head_name(text: str) -> str:
    for pattern in HEAD_NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip().strip("*").strip()
    return MISSING


def load_frontmatter(agent_path: Path, missing_files: list[str]) -> dict[str, str]:
    if not agent_path.is_file():
        missing_files.append(agent_path.relative_to(REPO_ROOT).as_posix())
        return {key: MISSING for key in FRONTMATTER_KEYS}
    data = parse_frontmatter(read_text(agent_path))
    for key in FRONTMATTER_KEYS:
        data.setdefault(key, MISSING)
    return data


def collect_team_records(missing_files: list[str]) -> list[RoleRecord]:
    records: list[RoleRecord] = []
    for soul_path in sorted(PROFILES_DIR.rglob("*.SOUL.md")):
        if soul_path.parent.name != "team":
            continue
        relative = soul_path.relative_to(PROFILES_DIR)
        dept = relative.parts[0]
        stem = soul_path.name[: -len(".SOUL.md")]
        if len(relative.parts) != 4 or relative.parts[2] != "team":
            print(
                f"error: unexpected team SOUL layout: {soul_path.relative_to(REPO_ROOT)}",
                file=sys.stderr,
            )
            missing_files.append(soul_path.relative_to(REPO_ROOT).as_posix())
            continue
        if dept not in HEAD_AGENT_SLUGS:
            print(f"error: team SOUL in unmapped department: {dept}", file=sys.stderr)
            missing_files.append(soul_path.relative_to(REPO_ROOT).as_posix())
            continue
        record = RoleRecord(dept, stem, soul_path)
        record.frontmatter = load_frontmatter(record.agent_path, missing_files)
        records.append(record)
    return records


def collect_heads(missing_files: list[str]) -> list[dict[str, str]]:
    heads: list[dict[str, str]] = []
    for dept in sorted(HEAD_AGENT_SLUGS):
        soul_path = PROFILES_DIR / dept / "SOUL.md"
        if not soul_path.is_file():
            print(
                f"error: missing head SOUL: {soul_path.relative_to(REPO_ROOT)}",
                file=sys.stderr,
            )
            missing_files.append(soul_path.relative_to(REPO_ROOT).as_posix())
            name = MISSING
        else:
            name = extract_head_name(read_text(soul_path))
        slug = HEAD_AGENT_SLUGS[dept]
        frontmatter = load_frontmatter(AGENTS_DIR / f"{slug}.md", missing_files)
        heads.append(
            {
                "dept": dept,
                "name": name,
                "slug": slug,
                "color": frontmatter["color"],
                "mode": frontmatter["mode"],
                "agents_md": frontmatter["agents_md"],
                "description": frontmatter["description"],
                "soul": soul_path.relative_to(REPO_ROOT).as_posix(),
                "frontmatter": frontmatter,
            }
        )
    return heads


def all_agent_files() -> list[str]:
    return sorted(
        Path(path).name[: -len(".md")] for path in glob.glob(str(AGENTS_DIR / "*.md"))
    )


def validate_track_coverage(records: list[RoleRecord]) -> list[str]:
    """Fail loudly if the roster grows past the hand-written TRACKS mapping."""
    track_depts = {dept for _, depts in TRACKS for dept in depts}
    errors: list[str] = []
    unknown = sorted(track_depts - set(HEAD_AGENT_SLUGS))
    if unknown:
        errors.append(f"TRACKS references unknown department(s): {', '.join(unknown)}")
    uncovered = sorted({record.dept for record in records} - track_depts)
    if uncovered:
        errors.append(f"department missing from TRACKS: {', '.join(uncovered)}")
    return errors


def render(
    heads: list[dict[str, str]],
    records: list[RoleRecord],
    agent_files: list[str],
) -> str:
    head_slugs = {head["slug"] for head in heads}
    team_slugs = {record.slug for record in records}
    team_agent_files = sorted(team_slugs - TEAM_HEAD_SHARED_SLUGS)
    mapped_slugs = sorted(head_slugs | team_slugs)
    unlisted = sorted(set(agent_files) - set(mapped_slugs))

    lines: list[str] = []
    add = lines.append

    add("# 📋 SoloCorp OS — Specialist Manifest v1.0")
    add("")
    add(f"> **Version:** {DOC_VERSION}  ")
    add("> **Generated by:** `scripts/generate-specialist-manifest.py` — **ห้ามแก้มือ**  ")
    add(
        "> **ขอบเขต:** roster ของ Department Heads และ specialist sub-agents จากข้อมูลจริงบนดิสก์"
    )
    add("")
    add("## 1. Snapshot")
    add("")
    add("| รายการ | จำนวน | หมายเหตุ |")
    add("|:-------|------:|:---------|")
    add(f"| Department Heads | {len(heads)} | `profiles/*/SOUL.md` |")
    add(f"| Team roles | {len(records)} | `profiles/**/team/*.SOUL.md` |")
    add(
        f"| Team agent files | {len(team_agent_files)} | "
        "67 team roles − `lead-researcher` (ใช้ head agent `rd-lab`); "
        "`ui-designer` เป็น slug เดียวกับ head dept 09 แต่ยังนับเป็น team file — "
        f"ไฟล์ agent ที่ไม่ซ้ำทั้ง manifest = {len(mapped_slugs)} |"
    )
    add(f"| Head agent files | {len(head_slugs)} | mapping dept → agent slug |")
    add(f"| Agent files ทั้งหมด | {len(agent_files)} | `.opencode/agents/*.md` |")
    add(
        f"| ไฟล์นอก manifest | {len(unlisted)} | "
        + (", ".join(code(slug) for slug in unlisted) if unlisted else "ไม่มี")
        + " |"
    )
    add("")
    if "cto" in unlisted:
        add(
            "> หมายเหตุ: `cto.md` มาจาก CTO Wave1 ที่ session อื่น staged ลบไว้ — "
            "ยังอยู่บนดิสก์จริง จึงถูกนับใน 87 จนกว่าการลบจะถูก merge"
        )
        add("")
    add("## 2. Runtime Contract")
    add("")
    add("Agent file ทุกไฟล์ต้องมี frontmatter 5 key ต่อไปนี้:")
    add("")
    add("| Key | ค่าที่คาดหวัง | ความหมาย |")
    add("|:----|:--------------|:---------|")
    add("| `name` | slug ตรงกับชื่อไฟล์ | ชื่อ agent ที่ runtime ใช้ resolve |")
    add("| `description` | ข้อความบรรทัดเดียว | คำอธิบายบทบาทสำหรับ UI / routing |")
    add("| `mode` | `subagent` | ต้องถูกเรียกผ่าน Head ไม่ใช่ primary |")
    add("| `agents_md` | `true` | ให้ runtime โหลด `AGENTS.md` ของ repo |")
    add('| `color` | hex `"#RRGGBB"` | สีประจำตัวใน UI |')
    add("")
    violation_rows = compliance_summary(heads, records, agent_files)
    for row in violation_rows:
        add(f"- {row}")
    add("")
    add(
        "> ค่า `MISSING` ในตาราง หมายถึง key/ไฟล์นั้นไม่มีอยู่จริงใน frontmatter — "
        "script ไม่เติมค่าที่เดาขึ้นเอง"
    )
    add("")

    add("## 3. Department Heads")
    add("")
    add("| Dept | Head name | Agent slug | Color | SOUL path |")
    add("|:-----|:----------|:-----------|:------|:----------|")
    for head in heads:
        add(
            "| {dept} | {name} | {slug} | {color} | {soul} |".format(
                dept=code(head["dept"]),
                name=escape_cell(head["name"]),
                slug=code(head["slug"]),
                color=code(head["color"]),
                soul=code(head["soul"]),
            )
        )
    add("")

    add("## 4. Specialist Teams")
    add("")
    section = 0
    for track_name, depts in TRACKS:
        section += 1
        dept_set = set(depts)
        rows = [record for record in records if record.dept in dept_set]
        rows.sort(key=lambda record: (record.dept, record.slug))
        add(f"### 4.{section} {track_name}")
        add("")
        depts_with_rows = {record.dept for record in rows}
        empty_depts = [dept for dept in depts if dept not in depts_with_rows]
        if empty_depts:
            add(
                "_ไม่มี team role ใน: "
                + ", ".join(code(dept) for dept in empty_depts)
                + " — dept นี้มีเฉพาะ head agent_"
            )
            add("")
        if not rows:
            add("_ไม่มี role ในสายนี้_")
            add("")
            continue
        add(
            "| Dept | Role (SOUL stem) | Agent slug | Color | Description | SOUL path |"
        )
        add(
            "|:-----|:-----------------|:-----------|:------|:------------|:----------|"
        )
        for record in rows:
            description = escape_cell(truncate(record.frontmatter["description"]))
            add(
                "| {dept} | {role} | {slug} | {color} | {description} | {soul} |".format(
                    dept=code(record.dept),
                    role=code(record.stem),
                    slug=code(record.slug),
                    color=code(record.frontmatter["color"]),
                    description=description,
                    soul=code(record.rel_soul),
                )
            )
        add("")

    add("## 5. Verification")
    add("")
    add("รันซ้ำแล้วต้องได้ไฟล์เดิมทุกครั้ง (deterministic — ไม่มี timestamp/commit hash):")
    add("")
    add("```bash")
    add("python3 scripts/generate-specialist-manifest.py")
    add("sha256sum docs/SPECIALIST-MANIFEST-v1.0.md")
    add("python3 scripts/generate-specialist-manifest.py")
    add("sha256sum docs/SPECIALIST-MANIFEST-v1.0.md")
    add("# → sha256 ทั้งสองรอบต้องเท่ากัน")
    add("```")
    add("")
    add("ผลนับจากไฟล์จริง:")
    add("")
    add(f"- Department Heads: **{len(heads)}**")
    add(f"- Team roles: **{len(records)}**")
    add(
        f"- Team agent files: **{len(team_agent_files)}** "
        "(67 team roles − `lead-researcher` ที่ใช้ head agent `rd-lab`; "
        f"`ui-designer` shared กับ head dept 09 → unique mapped files = {len(mapped_slugs)})"
    )
    add(f"- Head agent files: **{len(head_slugs)}**")
    add(f"- Agent files ทั้งหมด: **{len(agent_files)}**")
    add(
        f"- ไฟล์นอก manifest: **{len(unlisted)}**"
        + (f" — {', '.join(code(slug) for slug in unlisted)}" if unlisted else "")
    )
    add("")
    add("หลักการ:")
    add("")
    add("- ทุกค่าในตาราง (slug, color, description, ชื่อ head) อ่านจาก SOUL/agent files จริง")
    add("- `MISSING` = ไม่มีค่าหรือไฟล์นั้นบนดิสก์; script จะ exit 1 เมื่อไฟล์ที่ map ไว้หาย")
    add("- ลำดับแถว: dept ascending แล้ว slug ascending ภายในแต่ละ track")
    add("- ไม่มีการแก้เอกสารด้วยมือ — แก้ที่ script หรือข้อมูลต้นทางเท่านั้น")
    add("")

    return "\n".join(lines)


def compliance_summary(
    heads: list[dict[str, str]],
    records: list[RoleRecord],
    agent_files: list[str],
) -> list[str]:
    """Report the real frontmatter state instead of assuming the contract holds."""
    head_slugs = {head["slug"] for head in heads}
    team_slugs = {record.slug for record in records}
    mapped = sorted(head_slugs | team_slugs)
    missing_color: list[str] = []
    missing_agents_md: list[str] = []
    bad_name: list[str] = []
    bad_mode: list[str] = []
    for slug in mapped:
        frontmatter = _frontmatter_by_slug(slug, heads, records)
        if frontmatter["color"] == MISSING:
            missing_color.append(slug)
        if frontmatter["agents_md"] == MISSING:
            missing_agents_md.append(slug)
        if frontmatter["name"] != MISSING and frontmatter["name"] != slug:
            bad_name.append(f"{slug}→{frontmatter['name']}")
        if frontmatter["mode"] != MISSING and frontmatter["mode"] != "subagent":
            bad_mode.append(f"{slug}={frontmatter['mode']}")

    rows = [
        f"ไฟล์ agent ที่ map แล้ว (unique): **{len(mapped)}** จาก agent files ทั้งหมด "
        f"**{len(agent_files)}**",
        f"มี frontmatter ครบ 5 key: **{len(mapped) - len(set(missing_color) | set(missing_agents_md))}"
        f"/{len(mapped)}**",
    ]
    if missing_color:
        rows.append(
            "ขาด `color`/`agents_md`: "
            + ", ".join(
                code(slug)
                for slug in sorted(set(missing_color) | set(missing_agents_md))
            )
        )
    if bad_mode:
        rows.append(
            "`mode` ไม่ใช่ `subagent`: " + ", ".join(code(item) for item in bad_mode)
        )
    if bad_name:
        rows.append("`name` ไม่ตรงชื่อไฟล์: " + ", ".join(code(item) for item in bad_name))
    if not (missing_color or bad_mode or bad_name):
        rows.append("ไม่พบความเบี่ยงเบนจาก contract")
    return rows


def _frontmatter_by_slug(
    slug: str,
    heads: list[dict[str, str]],
    records: list[RoleRecord],
) -> dict[str, str]:
    for head in heads:
        if head["slug"] == slug:
            return head["frontmatter"]
    for record in records:
        if record.slug == slug:
            return record.frontmatter
    return {key: MISSING for key in FRONTMATTER_KEYS}


def main() -> int:
    missing_files: list[str] = []

    team_records = collect_team_records(missing_files)
    heads = collect_heads(missing_files)
    agent_files = all_agent_files()

    for message in validate_track_coverage(team_records):
        print(f"error: {message}", file=sys.stderr)
        missing_files.append(message)

    # Guard against a partially-scanned roster silently producing a smaller manifest.
    if not team_records:
        print("error: no team SOUL files found", file=sys.stderr)
        missing_files.append("profiles/**/team/*.SOUL.md")
    if not heads:
        print("error: no head SOUL files found", file=sys.stderr)
        missing_files.append("profiles/*/SOUL.md")
    if not agent_files:
        print("error: no agent files found", file=sys.stderr)
        missing_files.append(".opencode/agents/*.md")

    content = render(heads, team_records, agent_files)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    head_slugs = {head["slug"] for head in heads}
    team_slugs = {record.slug for record in team_records}
    mapped = head_slugs | team_slugs
    unlisted = sorted(set(agent_files) - mapped)

    print(f"generated: {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}")
    print(
        "heads={heads} team_roles={team_roles} team_agent_files={team_files} "
        "head_agent_files={head_files} agent_files={agent_files} unlisted={unlisted}".format(
            heads=len(heads),
            team_roles=len(team_records),
            team_files=len(team_slugs - TEAM_HEAD_SHARED_SLUGS),
            head_files=len(head_slugs),
            agent_files=len(agent_files),
            unlisted=len(unlisted),
        )
    )
    print(f"sha256={digest}")

    if missing_files:
        print("MISSING files:", file=sys.stderr)
        for item in sorted(set(missing_files)):
            print(f"  - {item}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Convert OpenCode-format @solocorp skills to Hermes standard and install.

Reads:   <repo>/skills/@solocorp/<cat>/<skill>/SKILL.md  (OpenCode frontmatter)
Writes:  ~/.hermes/skills/solocorp-<cat>-<skill>/SKILL.md (Hermes frontmatter)
         Body content is copied verbatim; only frontmatter is rebuilt.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent  # P1-4: dynamic (กัน hardcode /home/... vs /data/...)
SRC_ROOT = REPO / "skills" / "@solocorp"
DEST_ROOT = Path.home() / ".hermes" / "skills"

# One-line "Use when ..." descriptions derived from each skill's Purpose section.
DESCRIPTIONS = {
    "@solocorp/ceo/sprint-plan":
        "Use when a department needs a sprint plan template, progress report, or sprint status dashboard via the Central Bus.",
    "@solocorp/cfo/budget-check":
        "Use when a department needs budget checks, cost analysis, or ROI projection before starting a project.",
    "@solocorp/coo/daily-ops":
        "Use when the COO needs a daily ops report, to route requests to departments, or to scan SOP compliance.",
    "@solocorp/cross-dept/mirror-check":
        "Use when a department head must verify that a major decision reflects Dr.solodev Owner's identity and values before acting.",
    "@solocorp/cross-dept/pipeline-bridge":
        "Use when sending work across departments with structured handoff, audit trail, and automatic Mirror Check.",
    "@solocorp/engineering/deploy":
        "Use when engineering triggers a deploy, checks deployment status, or rolls back a service in SoloCorp OS.",
    "@solocorp/governance/rfc":
        "Use when creating or reviewing an RFC for changes impacting one or more departments in SoloCorp OS.",
    "@solocorp/qa/smoke-test":
        "Use when running smoke tests before deploy or health-checking services after deployment.",
}


def parse_opencode_frontmatter(text):
    """Split into (fm_dict_in_order, body)."""
    m = re.match(r"\A---\n(.*?)\n---\n?(.*)\Z", text, re.DOTALL)
    if not m:
        raise ValueError("no YAML frontmatter found")
    fm_raw, body = m.group(1), m.group(2)
    fm = {}
    for line in fm_raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        kv = line.split(":", 1)
        if len(kv) != 2:
            continue
        key = kv[0].strip()
        val = kv[1].strip().strip('"').strip("'")
        fm[key] = val
    return fm, body


def hermes_name(opencode_name):
    # "@solocorp/ceo/sprint-plan" -> "solocorp-ceo-sprint-plan"
    parts = opencode_name.strip('"').split("/")
    assert parts[0] == "@solocorp" and len(parts) == 3, f"bad name: {opencode_name}"
    return "-".join(["solocorp", parts[1], parts[2]])


def convert(src_path):
    text = src_path.read_text(encoding="utf-8")
    fm, body = parse_opencode_frontmatter(text)
    oc_name = fm["name"]
    h_name = hermes_name(oc_name)
    desc = DESCRIPTIONS[oc_name]
    assert desc.startswith("Use when ") and "\n" not in desc

    lines = ["---", f"name: {h_name}", f'description: "{desc}"']
    # Preserve useful OpenCode metadata as extra keys (Hermes ignores unknowns).
    # NOTE: do NOT carry over `platforms` — in Hermes it means OS platform
    # (linux/macos/windows); OpenCode values like [opencode, grok] would make
    # skill_matches_platform() filter the skill out on every OS. Absent = all.
    for key in ("version", "category", "trigger", "mirror_check"):
        if key in fm:
            v = fm[key]
            v = f'"{v}"' if key == "trigger" else v
            lines.append(f"{key}: {v}")
    lines.append("---")
    new_text = "\n".join(lines) + "\n" + body

    dest_dir = DEST_ROOT / h_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "SKILL.md"
    dest.write_text(new_text, encoding="utf-8")
    return oc_name, h_name, str(dest), body


def main():
    src_files = sorted(SRC_ROOT.glob("*/*/SKILL.md"))
    if len(src_files) != 8:
        print(f"FATAL: expected 8 SKILL.md, found {len(src_files)}", file=sys.stderr)
        sys.exit(1)

    rows = []
    for p in src_files:
        oc, h, dest, _body = convert(p)
        rows.append((oc, h, dest))
        print(f"OK  {oc}  ->  {h}  ({dest})")

    print("\n--- mapping ---")
    print("| OpenCode name | Hermes name |")
    print("|:--------------|:------------|")
    for oc, h, _ in rows:
        print(f"| `{oc}` | `{h}` |")

    # sanity: verify installed files parse & bodies match originals
    for p in src_files:
        orig_body = parse_opencode_frontmatter(p.read_text(encoding="utf-8"))[1]
        oc = re.search(r'name:\s*"(@solocorp/[^"]+)"', p.read_text(encoding="utf-8")).group(1)
        inst = (DEST_ROOT / hermes_name(oc) / "SKILL.md").read_text(encoding="utf-8")
        inst_fm, inst_body = parse_opencode_frontmatter(inst)
        assert inst_body == orig_body, f"body mismatch for {oc}"
        assert inst_fm["name"] == hermes_name(oc), f"name mismatch for {oc}"
        assert inst_fm["description"].startswith("Use when "), f"description bad for {oc}"
    print("\nVERIFIED: 8/8 installed — names valid, descriptions 'Use when ...', bodies byte-identical")


if __name__ == "__main__":
    main()

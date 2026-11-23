#!/usr/bin/env python3
"""Validate ``opencode.jsonc`` against what is actually on disk.

Five checks, each with an explicit, reviewed allowlist so a gap can never pass
silently:

1. ``skills-paths``        every path in ``skills.paths`` exists on disk, and
                           every skill on disk is reachable from one of those
                           paths — otherwise it is listed in
                           ``SKILLS_PATH_EXEMPT`` with a reason.
2. ``skill-id-collisions`` two directories defining one skill ID = a silent
                           override (the last configured source wins). Accepted
                           overrides must name the directory that wins in
                           ``SKILL_ID_OVERRIDE_ALLOWLIST``, so a path reorder
                           cannot quietly hand a skill to a shadow shim.
3. ``skill-manifest``      every loadable skill has a parsable ``skill.toml``
                           next to its ``SKILL.md``, or is listed in
                           ``SKILL_TOML_EXEMPT`` with a reason.
4. ``agents-coverage``     every Department Head in ``profiles/INDEX.md`` maps
                           (via ``HEAD_AGENT_MAP`` below) to an agent that
                           exists in ``opencode.jsonc`` → ``agents{}`` *and*
                           has a runtime file ``.opencode/agents/<agent>.md``.
                           Profiles without a head agent are listed in
                           ``PROFILES_EXEMPT`` with a reason. A head profile
                           with no mapping is a failure, so a new department
                           cannot land half-wired.
5. ``permission-lint``     an agent-level ``read * → allow`` rule is only
                           accepted for nodes in ``LEADERSHIP_ALLOWLIST``
                           (declared here with a reason). This check reports; it
                           never edits a block — agent-vs-global permission
                           precedence is proven in Wave 4 before any block is
                           narrowed.

Skill discovery follows the OpenCode skill rules (V2 docs, 2026-11-23):
a directory containing ``SKILL.md`` is one skill, grouping directories nest up
to six levels below a source root, and a directory that contains ``SKILL.md``
is not searched further. Flat ``*.md`` files directly under a source root are
skills too.

Usage
-----
    python3 scripts/validate-opencode-config.py                 # strict
    python3 scripts/validate-opencode-config.py --warn-only      # CI-first mode
    python3 scripts/validate-opencode-config.py --json           # machine-readable
    python3 scripts/validate-opencode-config.py --root OTHER     # another tree

Exit codes
----------
    0 = all checks pass (in ``--warn-only`` mode: findings are reported, still 0)
    1 = at least one finding in strict mode
    2 = config unreadable / unparsable / bad usage
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Allowlists — every entry needs a reason. Silence is never accidental.
# ─────────────────────────────────────────────────────────────────────────────

# Skills on disk that are deliberately NOT wired into ``skills.paths``.
# (Empty on 2026-11-23: `skills/@axis` is now a source root, so handoff-protocol —
# which keeps SKILL.md at its own folder root — is reachable. Keep the mechanism:
# a future third-party skill dropped under skills/ needs an entry here, with a reason.)
SKILLS_PATH_EXEMPT: dict[str, str] = {}

# Skill IDs that intentionally have no AXIS ``skill.toml`` (no bus binding).
SKILL_TOML_EXEMPT: dict[str, str] = {
    "earshot": "third-party skill pack — รัน local CLI/MCP เอง ไม่ผูก Central Bus (ไม่มี bus endpoint ให้ประกาศ)",
    "real-sound": "third-party skill pack — workflow การทำ soundtrack ไม่ผูก Central Bus",
    "voice-clone": "third-party skill pack — OmniVoice local runtime ไม่ผูก Central Bus",
    "ui-animation-review": "third-party skill pack — review checklist ไม่ผูก Central Bus",
    "meta-parallel-video": "third-party skill pack — render workflow ไม่ผูก Central Bus",
}

# profile slug (from profiles/INDEX.md) → agent id (opencode.jsonc agents{}).
# Mapping rule: 1 head profile = 1 head agent. The agent id is the runtime
# identity used everywhere else (rules/01-receive.md routing table, /workspace,
# session logs), so it is declared here instead of guessed from the folder name.
HEAD_AGENT_MAP: dict[str, str] = {
    "01-ceo": "ceo-turbo",
    "02-coo": "coo-kit",
    "02-cfo": "cfo-meetoo",
    "03-cmo": "cmo-mark",
    "04-orchestrator": "orchestrator-wut",
    "05-architect": "architect-songsak",
    "06-product": "product-produck",
    "07-engineering": "engineering-changful",
    "08-design": "design-kreet",
    "09-ui-designer": "ui-designer",
    "10-qa": "qa-team",
    "11-sales": "sales-team",
    "12-support": "support-team",
    "13-legal": "legal-tulya",
    "14-web3": "web3-aywa",
    "15-content-creator": "content-creator-sek",
    "16-neteng": "neteng-neet",
    "17-cybersec": "cybersec-sai",
    "18-psychology": "psych-jit",
    "19-rd-lab": "rd-lab",
}

# Three heads carry a jsonc key that differs from their runtime file stem
# (`agents.qa-team` vs `.opencode/agents/qa.md`). Kept as-is: renaming either
# side changes agent identity/permission scope, which Wave 4 owns once
# agent-vs-global precedence is proven. The mismatch is reported as a note.
RUNTIME_FILE_OVERRIDES: dict[str, str] = {
    "qa-team": "qa",
    "sales-team": "sales",
    "support-team": "support",
}

# Profiles that are not department heads by design.
PROFILES_EXEMPT: dict[str, str] = {
    "default": "Base/Fallback profile — ไม่มี head agent ของตัวเอง; default_agent คือ axis-ceo",
    "cto": (
        "C-Level dual-run (Wave1): runtime identity ประกาศที่ .opencode/agents/cto.md "
        "frontmatter เท่านั้น — ยังไม่มี jsonc block; การเพิ่ม/แคบ block รอ Wave 4 (precedence proof)"
    ),
}

# Nodes allowed to hold ``read * → allow``. Everything else must be scoped.
# Wave 4 owns widening/narrowing this list; this script only reports.
LEADERSHIP_ALLOWLIST: dict[str, str] = {
    "axis-ceo": "L4 primary controller — ต้องอ่านทุกบริบทเพื่อ route/decide",
    "ceo-turbo": "L4 primary controller (default_agent) — ต้องอ่านทุกบริบท",
    "coo-kit": "L3 gatekeeper — ตรวจงานทุกแผนกก่อนถึง CEO",
    "architect-songsak": "L2 system architect — audit bus/routing ทั้ง repo (existing block; Wave 4 re-check)",
    "cto": "C-Level technical command — md frontmatter (existing; Wave 4 re-check)",
    "cfo-meetoo": "md frontmatter ยังกว้าง, jsonc block แคบแล้ว — คงไว้ถึง Wave 4 (precedence proof)",
    "content-creator-sek": "md frontmatter ยังกว้าง, jsonc block แคบแล้ว — คงไว้ถึง Wave 4 (precedence proof)",
    "legal-tulya": "md frontmatter ยังกว้าง, jsonc block แคบแล้ว — คงไว้ถึง Wave 4 (precedence proof)",
    "orchestrator-wut": "md frontmatter ยังกว้าง, jsonc block แคบแล้ว — คงไว้ถึง Wave 4 (precedence proof)",
}

SKILL_SEARCH_DEPTH = (
    6  # OpenCode: "Search stops six directories below the source root."
)

# Skill IDs intentionally defined by more than one directory. OpenCode selects by
# ID and the LAST configured source wins, so this maps id → the directory that
# MUST win. Anything else is silent override and fails the gate.
SKILL_ID_OVERRIDE_ALLOWLIST: dict[str, tuple[str, str]] = {
    "deploy": (
        "skills/@axis/engineering/deploy",
        "CTO shadow shim skills/@axis/cto/deploy forwards to this skill — canonical must win; "
        "rename the cto shim dir before it can be loaded (Wave 4 / CTO)",
    ),
    "smoke-test": (
        "skills/@axis/qa/smoke-test",
        "CTO shadow shim skills/@axis/cto/smoke-test forwards to this skill — canonical must win; "
        "rename the cto shim dir before it can be loaded (Wave 4 / CTO)",
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# JSONC + skill discovery helpers
# ─────────────────────────────────────────────────────────────────────────────


def strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments and trailing commas, preserving strings."""
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    stripped = "".join(out)
    return re.sub(r",(\s*[}\]])", r"\1", stripped)


def load_config(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    return json.loads(strip_jsonc(raw))


def iter_skill_dirs(
    root: Path, max_depth: int = SKILL_SEARCH_DEPTH
) -> list[tuple[str, Path]]:
    """Ordered (skill id, directory) pairs for one source root (OpenCode rules).

    A list, not a dict: two directories inside the same root can share an ID,
    and that silent override must stay visible to ``skill-id-collisions``.
    """
    found: list[tuple[str, Path]] = []
    if not root.is_dir():
        return found

    for flat in sorted(root.glob("*.md")):
        if flat.name == "SKILL.md":
            continue
        if flat.name.startswith("."):
            continue
        found.append((flat.stem, root))

    def walk(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        if (directory / "SKILL.md").is_file():
            found.append((directory.name, directory))
            return  # a skill directory is never searched further
        try:
            children = sorted(p for p in directory.iterdir() if p.is_dir())
        except OSError:
            return
        for child in children:
            if child.name.startswith(".") or child.name == "node_modules":
                continue
            walk(child, depth + 1)

    walk(root, 1)
    return found


def skills_in_source(
    root: Path, max_depth: int = SKILL_SEARCH_DEPTH
) -> dict[str, Path]:
    """id → directory for one source root (last discovery wins, like OpenCode)."""
    return {skill_id: d for skill_id, d in iter_skill_dirs(root, max_depth)}


def skill_id_from_path(skill_dir: Path) -> str:
    return skill_dir.name


def all_skill_dirs_on_disk(root: Path) -> dict[str, Path]:
    """Every directory under skills/ that contains a SKILL.md."""
    out: dict[str, Path] = {}
    base = root / "skills"
    if not base.is_dir():
        return out
    for skill_md in sorted(base.rglob("SKILL.md")):
        out[skill_md.parent.name] = skill_md.parent
    return out


def parse_frontmatter_permissions(agent_md: Path) -> list[dict[str, str]]:
    """Read the ``permissions:`` list from an agent markdown frontmatter block."""
    text = agent_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        return []
    lines = match.group(1).splitlines()
    rules: list[dict[str, str]] = []
    in_block = False
    current: dict[str, str] = {}
    for line in lines:
        if re.match(r"^permissions:\s*$", line):
            in_block = True
            continue
        if not in_block:
            continue
        if line and not line.startswith((" ", "\t", "-")):
            break  # next top-level key
        item = re.match(r"^\s*-\s*action:\s*(.+?)\s*$", line)
        if item:
            if current:
                rules.append(current)
            current = {"action": item.group(1).strip("\"'")}
            continue
        kv = re.match(r"^\s+(resource|effect):\s*(.+?)\s*$", line)
        if kv and current:
            current[kv.group(1)] = kv.group(2).strip("\"'")
    if current:
        rules.append(current)
    return rules


# ─────────────────────────────────────────────────────────────────────────────
# Checks
# ─────────────────────────────────────────────────────────────────────────────


def collect_skill_sources(
    root: Path, paths: list[str]
) -> tuple[dict[str, list[Path]], list[str]]:
    """id → ordered distinct skill directories (last one wins in OpenCode)."""
    # A directory can be discovered again by a later, narrower source root
    # (e.g. skills/@axis then skills/@axis/engineering). Position matters, so
    # each directory keeps its LAST discovery index and buckets are rebuilt in
    # that order — otherwise a stale earlier index makes the wrong dir "win".
    positions: dict[str, dict[Path, int]] = {}
    missing: list[str] = []
    for idx, rel in enumerate(paths):
        target = (root / rel).resolve()
        if not target.is_dir():
            missing.append(f"path missing on disk: {rel} (skills.paths[{idx}])")
            continue
        for skill_id, skill_dir in iter_skill_dirs(target):
            positions.setdefault(skill_id, {})[skill_dir.resolve()] = idx

    sources = {
        skill_id: [d for d, _ in sorted(by_dir.items(), key=lambda kv: kv[1])]
        for skill_id, by_dir in positions.items()
    }
    return sources, missing


def check_skills_paths(root: Path, config: dict) -> dict:
    findings: list[str] = []
    notes: list[str] = []
    skills_cfg = config.get("skills", {})
    paths = (
        list(skills_cfg.get("paths", []))
        if isinstance(skills_cfg, dict)
        else list(skills_cfg)
    )

    sources, missing = collect_skill_sources(root, paths)
    findings.extend(missing)

    reachable_dirs = {d for dirs in sources.values() for d in dirs}
    on_disk = all_skill_dirs_on_disk(root)

    for skill_id, skill_dir in sorted(on_disk.items()):
        if skill_dir.resolve() in reachable_dirs:
            continue
        rel = str(skill_dir.relative_to(root))
        if rel in SKILLS_PATH_EXEMPT or skill_id in SKILLS_PATH_EXEMPT:
            continue
        findings.append(
            f"skill on disk not reachable from skills.paths: {rel} (id={skill_id})"
        )

    for exempt in sorted(SKILLS_PATH_EXEMPT):
        if exempt not in reachable_dirs and not (root / exempt).is_dir():
            findings.append(f"stale SKILLS_PATH_EXEMPT entry (no such dir): {exempt}")

    return {
        "id": "skills-paths",
        "status": "fail" if findings else "pass",
        "summary": f"{len(paths)} configured paths, {len(reachable_dirs)} skill dirs reachable, "
        f"{len(on_disk)} SKILL.md on disk, {len(SKILLS_PATH_EXEMPT)} path-exempt",
        "findings": findings,
        "notes": notes,
        "_sources": sources,
    }


def check_skill_id_collisions(sources: dict[str, list[Path]]) -> dict:
    """Two directories defining one skill ID = silent override (last path wins)."""
    findings: list[str] = []
    notes: list[str] = []
    colliding = {sid: dirs for sid, dirs in sources.items() if len(dirs) > 1}

    for skill_id, dirs in sorted(colliding.items()):
        declared = SKILL_ID_OVERRIDE_ALLOWLIST.get(skill_id)
        if declared is None:
            findings.append(
                f"skill id '{skill_id}' defined by {len(dirs)} directories "
                f"({', '.join(str(d) for d in dirs)}) — last one wins silently; "
                "rename a directory or declare SKILL_ID_OVERRIDE_ALLOWLIST"
            )
            continue
        expected_winner, reason = declared
        if not any(str(d).endswith(expected_winner) for d in dirs):
            findings.append(
                f"skill id '{skill_id}' allowlist expects {expected_winner} but that directory is not loaded"
            )
            continue
        if not str(dirs[-1]).endswith(expected_winner):
            findings.append(
                f"skill id '{skill_id}' is won by {dirs[-1]} but the canonical source is "
                f"{expected_winner} — reorder skills.paths (canonical must come last)"
            )
            continue
        notes.append(f"skill id '{skill_id}' override allowed: {expected_winner} wins — {reason}")

    return {
        "id": "skill-id-collisions",
        "status": "fail" if findings else "pass",
        "summary": f"{len(colliding)} duplicate skill id(s), "
        f"{len(SKILL_ID_OVERRIDE_ALLOWLIST)} declared override(s)",
        "findings": findings,
        "notes": notes,
    }


def check_skill_manifest(root: Path, sources: dict[str, list[Path]]) -> dict:
    findings: list[str] = []
    notes: list[str] = []
    with_manifest = 0
    exempt_seen = 0
    checked_dirs: set[Path] = set()

    for skill_id, dirs in sorted(sources.items()):
        for skill_dir in dirs:
            if skill_dir in checked_dirs:
                continue
            checked_dirs.add(skill_dir)
            manifest = skill_dir / "skill.toml"
            if not manifest.is_file():
                if skill_id in SKILL_TOML_EXEMPT:
                    exempt_seen += 1
                    continue
                findings.append(
                    f"missing skill.toml: {skill_dir.relative_to(root.resolve())} (id={skill_id})"
                )
                continue
            try:
                data = tomllib.loads(manifest.read_text(encoding="utf-8"))
            except tomllib.TOMLDecodeError as exc:
                findings.append(
                    f"unparsable skill.toml: {manifest.relative_to(root.resolve())} — {exc}"
                )
                continue
            with_manifest += 1
            skill_section = data.get("skill", {})
            for key in ("name", "version", "description"):
                if not skill_section.get(key):
                    findings.append(
                        f"skill.toml missing [skill].{key}: {manifest.relative_to(root.resolve())}"
                    )

    on_disk = all_skill_dirs_on_disk(root)
    for exempt in sorted(SKILL_TOML_EXEMPT):
        if exempt not in sources and exempt not in on_disk:
            findings.append(f"stale SKILL_TOML_EXEMPT entry (no such skill): {exempt}")

    return {
        "id": "skill-manifest",
        "status": "fail" if findings else "pass",
        "summary": f"{with_manifest} manifests valid, {exempt_seen} exempt, "
        f"{len(SKILL_TOML_EXEMPT)} declared exemptions",
        "findings": findings,
        "notes": notes,
    }


def head_profiles_from_index(root: Path) -> list[str]:
    """Profile slugs that represent heads, parsed from profiles/INDEX.md.

    Only table rows whose first cell is a profile slug (``NN-name`` or ``cto``
    or ``default``) count — team tables start with a plain number instead.
    """
    index = root / "profiles" / "INDEX.md"
    if not index.is_file():
        return []
    slugs: list[str] = []
    row_re = re.compile(
        r"^\|\s*`?(?:\d{2}-[a-z0-9-]+|cto|default)`?\s*\|", re.MULTILINE
    )
    for match in row_re.finditer(index.read_text(encoding="utf-8")):
        line = match.group(0)
        slug = line.strip("| \t\n").strip("`").strip()
        if slug and slug not in slugs:
            slugs.append(slug)
    return slugs


def check_agents_coverage(root: Path, config: dict) -> dict:
    findings: list[str] = []
    notes: list[str] = []
    agents = config.get("agents", {}) or {}
    profiles = head_profiles_from_index(root)

    if not profiles:
        findings.append("profiles/INDEX.md not found or no profile rows parsed")

    covered = 0
    for profile in profiles:
        if profile in PROFILES_EXEMPT:
            continue
        agent_id = HEAD_AGENT_MAP.get(profile)
        if not agent_id:
            findings.append(
                f"head profile has no HEAD_AGENT_MAP entry: {profile} "
                "(เพิ่ม mapping ใน scripts/validate-opencode-config.py หรือประกาศ exempt)"
            )
            continue
        if agent_id not in agents:
            findings.append(
                f"head profile {profile} → agent '{agent_id}' missing from opencode.jsonc agents{{}}"
            )
            continue
        runtime_stem = RUNTIME_FILE_OVERRIDES.get(agent_id, agent_id)
        runtime_file = root / ".opencode" / "agents" / f"{runtime_stem}.md"
        if not runtime_file.is_file():
            findings.append(
                f"head profile {profile} → agent '{agent_id}' has no runtime file {runtime_file.relative_to(root)}"
            )
            continue
        if runtime_stem != agent_id:
            notes.append(
                f"agent id '{agent_id}' (opencode.jsonc) ≠ runtime file '{runtime_stem}.md' — "
                "id/permission alignment deferred to Wave 4"
            )
        covered += 1

    for profile in sorted(HEAD_AGENT_MAP):
        if profiles and profile not in profiles:
            findings.append(
                f"stale HEAD_AGENT_MAP entry (profile not in INDEX.md): {profile}"
            )

    for profile in sorted(PROFILES_EXEMPT):
        if profiles and profile not in profiles:
            findings.append(
                f"stale PROFILES_EXEMPT entry (profile not in INDEX.md): {profile}"
            )

    for agent_id in sorted(RUNTIME_FILE_OVERRIDES):
        if agent_id not in agents:
            findings.append(
                f"stale RUNTIME_FILE_OVERRIDES entry (agent not in agents{{}}): {agent_id}"
            )

    return {
        "id": "agents-coverage",
        "status": "fail" if findings else "pass",
        "summary": f"{covered} head profiles wired, {len(PROFILES_EXEMPT)} exempt, "
        f"{len(agents)} agents declared",
        "findings": findings,
        "notes": notes,
    }


def check_permission_lint(root: Path, config: dict) -> dict:
    findings: list[str] = []
    notes: list[str] = []
    checked = 0

    def is_broad_read(rule: dict) -> bool:
        return (
            rule.get("action") == "read"
            and rule.get("resource") == "*"
            and rule.get("effect") == "allow"
        )

    for agent_id, block in sorted((config.get("agents") or {}).items()):
        for rule in (block or {}).get("permissions") or []:
            if not is_broad_read(rule):
                continue
            checked += 1
            if agent_id not in LEADERSHIP_ALLOWLIST:
                findings.append(
                    f"opencode.jsonc agents.{agent_id} uses read * → allow "
                    "but is not in LEADERSHIP_ALLOWLIST"
                )

    agents_dir = root / ".opencode" / "agents"
    if agents_dir.is_dir():
        for md in sorted(agents_dir.glob("*.md")):
            for rule in parse_frontmatter_permissions(md):
                if not is_broad_read(rule):
                    continue
                checked += 1
                if md.stem not in LEADERSHIP_ALLOWLIST:
                    findings.append(
                        f"{md.relative_to(root)} frontmatter uses read * → allow "
                        f"but '{md.stem}' is not in LEADERSHIP_ALLOWLIST"
                    )

    return {
        "id": "permission-lint",
        "status": "fail" if findings else "pass",
        "summary": f"{checked} broad read grants reviewed, "
        f"{len(LEADERSHIP_ALLOWLIST)} allowlisted nodes",
        "findings": findings,
        "notes": notes,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────


def run_checks(root: Path) -> list[dict]:
    config_path = root / "opencode.jsonc"
    if not config_path.is_file():
        legacy = root / "opencode.json"
        if legacy.is_file():
            config_path = legacy
        else:
            raise FileNotFoundError(f"no opencode.jsonc/opencode.json under {root}")
    config = load_config(config_path)

    skills_check = check_skills_paths(root, config)
    sources = skills_check.pop("_sources")
    return [
        skills_check,
        check_skill_id_collisions(sources),
        check_skill_manifest(root, sources),
        check_agents_coverage(root, config),
        check_permission_lint(root, config),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate opencode config against the repo"
    )
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="report findings but exit 0 (CI first phase)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    try:
        checks = run_checks(root)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"config-lint: cannot validate — {exc}", file=sys.stderr)
        return 2

    failed = [c for c in checks if c["status"] == "fail"]
    ok = not failed

    if args.json:
        print(
            json.dumps(
                {
                    "ok": ok,
                    "warn_only": args.warn_only,
                    "root": str(root),
                    "checks": checks,
                    "failed": [c["id"] for c in failed],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"opencode config validation — root={root}")
        for check in checks:
            mark = (
                "PASS"
                if check["status"] == "pass"
                else ("WARN" if args.warn_only else "FAIL")
            )
            print(f"[{mark}] {check['id']}: {check['summary']}")
            for note in check.get("notes") or []:
                print(f"       · note: {note}")
            for finding in check["findings"]:
                print(f"       - {finding}")
        total = sum(len(c["findings"]) for c in checks)
        print(
            f"result: {'OK' if ok else ('WARN-ONLY — ' + str(total) + ' finding(s)') if args.warn_only else str(total) + ' finding(s)'}"
        )

    if ok:
        return 0
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    sys.exit(main())

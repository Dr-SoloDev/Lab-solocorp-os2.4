"""Guard for ``docs/SPECIALIST-MANIFEST-v1.0.md`` and its generator.

The manifest claims "ห้ามแก้มือ" (never hand-edited). Nothing enforced that
before this file: a hand edit or a roster change silently made the document
lie. These tests make the claim checkable.

Coverage map:

* drift      — committed document must equal a fresh render, byte for byte
* determinism— two renders must be identical (no timestamp/commit hash)
* roster     — every mapped agent file exists; counts never shrink
* contract   — all mapped agents carry the 5 keys; only declared agents are primary
* --check    — 0 clean, 2 stale/missing/unknown argument
* accounting — compliance counts *all five* keys, not just color/agents_md
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "generate-specialist-manifest.py"

EXPECTED_HEADS = 20
MIN_TEAM_ROLES = 67
# 2026-11-19 rollback removed .opencode/agents/cto.md (86 agent files remain).
MIN_AGENT_FILES = 86
ALLOWED_UNLISTED = {"axis-ceo"}


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_specialist_manifest", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _load_generator()


def _repo_state():
    missing: list[str] = []
    records = gen.collect_team_records(missing)
    heads = gen.collect_heads(missing)
    agent_files = gen.all_agent_files()
    return missing, records, heads, agent_files


# ── roster ────────────────────────────────────────────────────────────


def test_every_mapped_source_file_exists():
    missing, records, heads, agent_files = _repo_state()
    assert missing == [], f"generator reported missing sources: {missing}"
    assert len(heads) == EXPECTED_HEADS
    assert len(records) >= MIN_TEAM_ROLES, "team roster shrank — check the glob"
    assert len(agent_files) >= MIN_AGENT_FILES, "agent files disappeared"


def test_unlisted_agents_are_the_declared_allowlist():
    _, records, heads, agent_files = _repo_state()
    mapped = {head["slug"] for head in heads} | {record.slug for record in records}
    assert set(agent_files) - mapped <= ALLOWED_UNLISTED


# ── drift + determinism ───────────────────────────────────────────────


def test_committed_manifest_matches_generator():
    _, records, heads, agent_files = _repo_state()
    rendered = gen.render(heads, records, agent_files)
    committed = gen.OUTPUT_PATH.read_text(encoding="utf-8")
    assert committed == rendered, (
        "docs/SPECIALIST-MANIFEST-v1.0.md is stale — run "
        "`python3 scripts/generate-specialist-manifest.py`"
    )


def test_generation_is_deterministic():
    _, records, heads, agent_files = _repo_state()
    first = gen.render(heads, records, agent_files)
    second = gen.render(heads, records, agent_files)
    assert first == second


# ── --check mode ──────────────────────────────────────────────────────


def test_check_mode_accepts_a_clean_tree(capsys):
    assert gen.main(["--check"]) == 0
    assert "up-to-date" in capsys.readouterr().out


def test_check_mode_detects_a_stale_document(monkeypatch, tmp_path, capsys):
    target = tmp_path / "manifest.md"
    target.write_text("hand-edited\n", encoding="utf-8")
    monkeypatch.setattr(gen, "OUTPUT_PATH", target)
    assert gen.main(["--check"]) == 2
    assert "stale" in capsys.readouterr().err


def test_check_mode_detects_a_missing_document(monkeypatch, tmp_path):
    monkeypatch.setattr(gen, "OUTPUT_PATH", tmp_path / "absent.md")
    assert gen.main(["--check"]) == 2


def test_unknown_argument_is_rejected(capsys):
    assert gen.main(["--bogus"]) == 2
    assert "unknown argument" in capsys.readouterr().err


# ── runtime contract ──────────────────────────────────────────────────


def test_all_mapped_agents_carry_the_five_contract_keys():
    _, records, heads, agent_files = _repo_state()
    mapped = {head["slug"] for head in heads} | {record.slug for record in records}
    rows = gen.compliance_summary(heads, records, agent_files)
    assert f"มี key ครบ 5 ตัว: **{len(mapped)}/{len(mapped)}**" in rows, rows


def test_primary_mode_is_only_the_declared_exceptions():
    _, records, heads, agent_files = _repo_state()
    primary = set()
    for head in heads:
        if head["frontmatter"].get("mode") not in (gen.MISSING, "subagent"):
            primary.add(head["slug"])
    for record in records:
        if record.frontmatter.get("mode") not in (gen.MISSING, "subagent"):
            primary.add(record.slug)
    assert primary == set(gen.INTENTIONAL_PRIMARY_SLUGS)


# ── compliance accounting (regression: only color/agents_md were counted) ──


def _full_frontmatter(slug: str) -> dict[str, str]:
    return {
        "name": slug,
        "description": f"{slug} description",
        "mode": "subagent",
        "agents_md": "true",
        "color": '"#123456"',
    }


def test_compliance_counts_a_missing_description():
    head = {"slug": "head-a", "frontmatter": _full_frontmatter("head-a")}
    team = SimpleNamespace(
        slug="team-b",
        frontmatter={**_full_frontmatter("team-b"), "description": gen.MISSING},
    )
    rows = gen.compliance_summary([head], [team], ["head-a.md", "team-b.md"])
    assert "มี key ครบ 5 ตัว: **1/2**" in rows, rows
    assert any("ขาด `description`" in row for row in rows), rows


def test_compliance_counts_a_missing_mode():
    head = {"slug": "head-a", "frontmatter": _full_frontmatter("head-a")}
    team = SimpleNamespace(
        slug="team-b",
        frontmatter={**_full_frontmatter("team-b"), "mode": gen.MISSING},
    )
    rows = gen.compliance_summary([head], [team], ["head-a.md", "team-b.md"])
    assert "มี key ครบ 5 ตัว: **1/2**" in rows, rows
    assert any("ขาด `mode`" in row for row in rows), rows


def test_compliance_labels_declared_primary_as_intentional():
    head = {
        "slug": "ceo-turbo",
        "frontmatter": {**_full_frontmatter("ceo-turbo"), "mode": "primary"},
    }
    rows = gen.compliance_summary([head], [], ["ceo-turbo.md"])
    assert any("ตั้งใจ" in row for row in rows), rows
    assert not any("ไม่ตั้งใจ" in row for row in rows), rows


def test_compliance_flags_an_undeclared_primary():
    head = {
        "slug": "rogue-agent",
        "frontmatter": {**_full_frontmatter("rogue-agent"), "mode": "primary"},
    }
    rows = gen.compliance_summary([head], [], ["rogue-agent.md"])
    assert any("ไม่ตั้งใจ" in row for row in rows), rows


def test_compliance_reports_name_mismatch():
    head = {
        "slug": "head-a",
        "frontmatter": {**_full_frontmatter("head-a"), "name": "other-name"},
    }
    rows = gen.compliance_summary([head], [], ["head-a.md"])
    assert any("name" in row and "ไม่ตรง" in row for row in rows), rows


# ── rendering details ─────────────────────────────────────────────────


def test_snapshot_team_role_count_is_derived():
    _, records, heads, agent_files = _repo_state()
    trimmed = records[:-1]
    rendered = gen.render(heads, trimmed, agent_files)
    assert f"{len(trimmed)} team roles" in rendered
    assert f"{len(records)} team roles" not in rendered


def test_cto_note_count_is_derived():
    _, records, heads, agent_files = _repo_state()
    # Simulate an unlisted cto.md (the real file was removed by the 2026-11-19
    # rollback); the note must derive its count from the list it is given.
    synthetic = [*agent_files, "cto"]
    trimmed = [slug for slug in synthetic if slug != "axis-ceo"]
    rendered = gen.render(heads, records, trimmed)
    assert "`cto.md`" in rendered
    assert f"จึงถูกนับใน {len(trimmed)}" in rendered
    assert f"จึงถูกนับใน {len(synthetic)}" not in rendered


def test_manifest_reports_counts_derived_from_disk():
    _, records, heads, agent_files = _repo_state()
    content = gen.OUTPUT_PATH.read_text(encoding="utf-8")
    assert f"{len(records)} team roles" in content
    assert f"**{len(agent_files)}**" in content


def test_escape_cell_escapes_pipe_and_backslash():
    assert gen.escape_cell("a|b") == "a\\|b"
    assert gen.escape_cell("a\\b") == "a\\\\b"


def test_parse_frontmatter_unquotes_values():
    text = '---\nname: "x"\ncolor: "#fff"\n---\n'
    assert gen.parse_frontmatter(text) == {"name": "x", "color": "#fff"}


def test_track_coverage_rejects_an_undeclared_head_only_department(monkeypatch):
    monkeypatch.setitem(gen.HEAD_AGENT_SLUGS, "20-new", "new-head")
    errors = gen.validate_track_coverage([])
    assert any("HEAD_ONLY_DEPTS" in error for error in errors), errors

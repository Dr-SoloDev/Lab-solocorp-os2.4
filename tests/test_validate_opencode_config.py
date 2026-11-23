"""Tests for scripts/validate-opencode-config.py (Wave 2 config drift gate).

Two layers:
1. Unit — each check against a synthetic repo built in ``tmp_path`` (valid tree
   first, then one thing broken per test), plus the JSONC/skill-discovery helpers.
2. Integration — the validator run for real against THIS repository, strict,
   must exit 0. That is the same command CI runs after the 2026-11-30 flip.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "validate-opencode-config.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_opencode_config", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


voc = _load_module()


# ── fixture builders ────────────────────────────────────────────────────────


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _index_md(extra_profiles: list[str] | None = None) -> str:
    """INDEX.md whose head rows cover HEAD_AGENT_MAP (so no stale-map findings)."""
    rows = [
        "# AXIS — Profile Index",
        "",
        "## Department Heads",
        "",
        "| # | Profile |",
        "|:--|:--|",
    ]
    for slug in list(voc.HEAD_AGENT_MAP) + list(extra_profiles or []):
        rows.append(f"| `{slug}` | **Head** |")
    rows.append("| `default` | **Default (Fallback)** |")
    # a team table — must NOT be parsed as head profiles
    rows += [
        "",
        "## Team — 05-architect",
        "",
        "| # | Agent |",
        "|:-:|:------|",
        "| 01 | [Pipeline Auditor](x/pipeline-auditor.SOUL.md) |",
    ]
    return "\n".join(rows) + "\n"


def _runtime_stem(agent_id: str) -> str:
    return voc.RUNTIME_FILE_OVERRIDES.get(agent_id, agent_id)


def build_valid_repo(root: Path) -> Path:
    """A minimal tree that passes all four checks."""
    agents = {agent_id: {} for agent_id in voc.HEAD_AGENT_MAP.values()}
    agents["ceo-turbo"]["permissions"] = [
        {"action": "read", "resource": "*", "effect": "allow"}
    ]
    config = {
        "$schema": "https://opencode.ai/config.json",
        "agents": agents,
        "skills": {"paths": ["skills/@axis"]},
    }
    _write(root / "opencode.jsonc", json.dumps(config, indent=2))
    _write(root / "profiles" / "INDEX.md", _index_md())
    for agent_id in agents:
        _write(
            root / ".opencode" / "agents" / f"{_runtime_stem(agent_id)}.md",
            f"---\nname: {_runtime_stem(agent_id)}\nmode: subagent\n---\n\n# {agent_id}\n",
        )
    _write(
        root / "skills" / "@axis" / "demo" / "SKILL.md",
        "---\nname: demo\n---\n\n# demo\n",
    )
    _write(
        root / "skills" / "@axis" / "demo" / "skill.toml",
        '[skill]\nname = "@axis/demo"\nversion = "0.1.0"\ndescription = "demo"\n',
    )
    return root


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch) -> Path:
    """Valid synthetic tree with the real allowlists scoped to what the tree holds.

    The production allowlists name real third-party skills / the cto profile, so
    they are narrowed here; individual tests re-add entries via monkeypatch.
    """
    monkeypatch.setattr(voc, "SKILL_TOML_EXEMPT", {})
    monkeypatch.setattr(voc, "SKILLS_PATH_EXEMPT", {})
    monkeypatch.setattr(voc, "PROFILES_EXEMPT", {"default": "fallback profile"})
    return build_valid_repo(tmp_path)


def _check(checks: list[dict], check_id: str) -> dict:
    for check in checks:
        if check["id"] == check_id:
            return check
    raise AssertionError(f"check {check_id} not produced")


# ── helper unit tests ───────────────────────────────────────────────────────


class TestStripJsonc:
    def test_removes_line_and_block_comments(self) -> None:
        raw = '{\n  // line\n  "a": 1, /* block */\n  "b": 2\n}'
        assert json.loads(voc.strip_jsonc(raw)) == {"a": 1, "b": 2}

    def test_preserves_comment_like_text_inside_strings(self) -> None:
        raw = '{"url": "https://x.dev//y", "glob": "a/*b*/c"}'
        assert json.loads(voc.strip_jsonc(raw)) == {
            "url": "https://x.dev//y",
            "glob": "a/*b*/c",
        }

    def test_removes_trailing_commas(self) -> None:
        raw = '{"a": [1, 2,], "b": {"c": 3,},}'
        assert json.loads(voc.strip_jsonc(raw)) == {"a": [1, 2], "b": {"c": 3}}

    def test_real_config_parses(self) -> None:
        cfg = voc.load_config(REPO_ROOT / "opencode.jsonc")
        assert cfg["agents"], "agents{} must survive JSONC stripping"
        assert cfg["skills"]["paths"]


class TestSkillDiscovery:
    def test_nested_grouping_and_flat_md(self, tmp_path: Path) -> None:
        _write(tmp_path / "skills" / "flat.md", "x")
        _write(tmp_path / "skills" / "group" / "deep" / "SKILL.md", "x")
        found = voc.skills_in_source(tmp_path / "skills")
        assert set(found) == {"flat", "deep"}

    def test_skill_dir_is_not_searched_further(self, tmp_path: Path) -> None:
        """A directory containing SKILL.md is one skill — inner SKILL.md is not another."""
        _write(tmp_path / "src" / "outer" / "SKILL.md", "x")
        _write(tmp_path / "src" / "outer" / "inner" / "SKILL.md", "x")
        found = voc.skills_in_source(tmp_path / "src")
        assert set(found) == {"outer"}

    def test_depth_limit_six(self, tmp_path: Path) -> None:
        too_deep = tmp_path / "src" / "a" / "b" / "c" / "d" / "e" / "f" / "g"
        _write(too_deep / "SKILL.md", "x")
        assert voc.skills_in_source(tmp_path / "src") == {}

    def test_missing_source_root_returns_empty(self, tmp_path: Path) -> None:
        assert voc.skills_in_source(tmp_path / "nope") == {}


class TestIndexParsing:
    def test_only_head_rows_are_profiles(self, tmp_path: Path) -> None:
        _write(tmp_path / "profiles" / "INDEX.md", _index_md())
        profiles = voc.head_profiles_from_index(tmp_path)
        assert "01-ceo" in profiles
        assert "default" in profiles
        assert "01" not in profiles  # team table row
        assert "pipeline-auditor" not in profiles

    def test_missing_index_returns_empty(self, tmp_path: Path) -> None:
        assert voc.head_profiles_from_index(tmp_path) == []


# ── check: skills-paths ─────────────────────────────────────────────────────


class TestSkillsPaths:
    def test_valid_repo_passes(self, repo: Path) -> None:
        checks = voc.run_checks(repo)
        assert _check(checks, "skills-paths")["status"] == "pass"

    def test_missing_path_fails(self, repo: Path) -> None:
        cfg = json.loads(voc.strip_jsonc((repo / "opencode.jsonc").read_text()))
        cfg["skills"]["paths"].append("skills/@axis/does-not-exist")
        _write(repo / "opencode.jsonc", json.dumps(cfg))
        check = _check(voc.run_checks(repo), "skills-paths")
        assert check["status"] == "fail"
        assert any("does-not-exist" in f for f in check["findings"])

    def test_unreachable_skill_fails(self, repo: Path) -> None:
        _write(repo / "skills" / "orphan" / "SKILL.md", "---\nname: orphan\n---\n")
        check = _check(voc.run_checks(repo), "skills-paths")
        assert check["status"] == "fail"
        assert any("orphan" in f for f in check["findings"])

    def test_exempt_unreachable_skill_passes(self, repo: Path, monkeypatch) -> None:
        _write(repo / "skills" / "orphan" / "SKILL.md", "---\nname: orphan\n---\n")
        monkeypatch.setitem(voc.SKILLS_PATH_EXEMPT, "skills/orphan", "third-party pack")
        assert _check(voc.run_checks(repo), "skills-paths")["status"] == "pass"

    def test_stale_exempt_entry_fails(self, repo: Path, monkeypatch) -> None:
        monkeypatch.setitem(voc.SKILLS_PATH_EXEMPT, "skills/ghost", "gone")
        check = _check(voc.run_checks(repo), "skills-paths")
        assert check["status"] == "fail"
        assert any("stale" in f for f in check["findings"])


# ── check: skill-id-collisions ──────────────────────────────────────────────


class TestSkillIdCollisions:
    def test_valid_repo_passes(self, repo: Path) -> None:
        assert _check(voc.run_checks(repo), "skill-id-collisions")["status"] == "pass"

    def test_same_dir_seen_twice_is_not_a_collision(self, repo: Path) -> None:
        cfg = json.loads(voc.strip_jsonc((repo / "opencode.jsonc").read_text()))
        cfg["skills"]["paths"] = ["skills/@axis", "skills/@axis/demo"]
        _write(repo / "opencode.jsonc", json.dumps(cfg))
        check = _check(voc.run_checks(repo), "skill-id-collisions")
        assert check["status"] == "pass"

    def test_two_dirs_same_id_in_one_root_fails(self, repo: Path) -> None:
        _write(repo / "skills" / "@axis" / "other" / "demo" / "SKILL.md", "x")
        _write(
            repo / "skills" / "@axis" / "other" / "demo" / "skill.toml",
            '[skill]\nname = "demo2"\nversion = "0.1.0"\ndescription = "x"\n',
        )
        check = _check(voc.run_checks(repo), "skill-id-collisions")
        assert check["status"] == "fail"
        assert any("'demo'" in f for f in check["findings"])

    def test_shadow_source_listed_last_fails_when_not_allowlisted(
        self, repo: Path
    ) -> None:
        # a second root defining the same id, listed after the canonical one
        _write(repo / "skills" / "@axis" / "shim" / "demo" / "SKILL.md", "x")
        _write(
            repo / "skills" / "@axis" / "shim" / "demo" / "skill.toml",
            '[skill]\nname = "shim"\nversion = "0.1.0"\ndescription = "x"\n',
        )
        cfg = json.loads(voc.strip_jsonc((repo / "opencode.jsonc").read_text()))
        cfg["skills"]["paths"] = ["skills/@axis", "skills/@axis/shim"]
        _write(repo / "opencode.jsonc", json.dumps(cfg))
        check = _check(voc.run_checks(repo), "skill-id-collisions")
        assert check["status"] == "fail"

    def test_allowlist_fails_when_canonical_does_not_win(
        self, repo: Path, monkeypatch
    ) -> None:
        _write(repo / "skills" / "@axis" / "canon" / "demo" / "SKILL.md", "x")
        _write(
            repo / "skills" / "@axis" / "canon" / "demo" / "skill.toml",
            '[skill]\nname = "canon"\nversion = "0.1.0"\ndescription = "x"\n',
        )
        cfg = json.loads(voc.strip_jsonc((repo / "opencode.jsonc").read_text()))
        cfg["skills"]["paths"] = ["skills/@axis", "skills/@axis/canon"]
        _write(repo / "opencode.jsonc", json.dumps(cfg))
        monkeypatch.setitem(
            voc.SKILL_ID_OVERRIDE_ALLOWLIST,
            "demo",
            ("skills/@axis/demo", "canonical demo must win"),
        )
        check = _check(voc.run_checks(repo), "skill-id-collisions")
        assert check["status"] == "fail"
        assert any("reorder skills.paths" in f for f in check["findings"])

    def test_allowlist_passes_with_note_when_canonical_wins(
        self, repo: Path, monkeypatch
    ) -> None:
        _write(repo / "shadow" / "demo" / "SKILL.md", "x")
        _write(
            repo / "shadow" / "demo" / "skill.toml",
            '[skill]\nname = "shadow"\nversion = "0.1.0"\ndescription = "x"\n',
        )
        cfg = json.loads(voc.strip_jsonc((repo / "opencode.jsonc").read_text()))
        cfg["skills"]["paths"] = ["shadow", "skills/@axis"]
        _write(repo / "opencode.jsonc", json.dumps(cfg))
        monkeypatch.setitem(
            voc.SKILL_ID_OVERRIDE_ALLOWLIST,
            "demo",
            ("skills/@axis/demo", "canonical demo must win"),
        )
        check = _check(voc.run_checks(repo), "skill-id-collisions")
        assert check["status"] == "pass"
        assert any("override allowed" in n for n in check["notes"])

    def test_allowlist_entry_pointing_at_missing_dir_fails(
        self, repo: Path, monkeypatch
    ) -> None:
        _write(repo / "skills" / "@axis" / "shim" / "demo" / "SKILL.md", "x")
        _write(
            repo / "skills" / "@axis" / "shim" / "demo" / "skill.toml",
            '[skill]\nname = "shim"\nversion = "0.1.0"\ndescription = "x"\n',
        )
        monkeypatch.setitem(
            voc.SKILL_ID_OVERRIDE_ALLOWLIST, "demo", ("skills/nowhere/demo", "gone")
        )
        check = _check(voc.run_checks(repo), "skill-id-collisions")
        assert check["status"] == "fail"


# ── check: skill-manifest ───────────────────────────────────────────────────


class TestSkillManifest:
    def test_valid_repo_passes(self, repo: Path) -> None:
        assert _check(voc.run_checks(repo), "skill-manifest")["status"] == "pass"

    def test_missing_manifest_fails(self, repo: Path) -> None:
        _write(
            repo / "skills" / "@axis" / "bare" / "SKILL.md", "---\nname: bare\n---\n"
        )
        check = _check(voc.run_checks(repo), "skill-manifest")
        assert check["status"] == "fail"
        assert any("bare" in f and "skill.toml" in f for f in check["findings"])

    def test_exempt_manifest_passes(self, repo: Path, monkeypatch) -> None:
        _write(
            repo / "skills" / "@axis" / "bare" / "SKILL.md", "---\nname: bare\n---\n"
        )
        monkeypatch.setitem(voc.SKILL_TOML_EXEMPT, "bare", "third-party")
        assert _check(voc.run_checks(repo), "skill-manifest")["status"] == "pass"

    def test_unparsable_manifest_fails(self, repo: Path) -> None:
        _write(repo / "skills" / "@axis" / "demo" / "skill.toml", "[skill\nname=")
        check = _check(voc.run_checks(repo), "skill-manifest")
        assert check["status"] == "fail"
        assert any("unparsable" in f for f in check["findings"])

    def test_manifest_missing_required_keys_fails(self, repo: Path) -> None:
        _write(
            repo / "skills" / "@axis" / "demo" / "skill.toml", '[skill]\nname = "x"\n'
        )
        check = _check(voc.run_checks(repo), "skill-manifest")
        assert check["status"] == "fail"
        assert any("[skill].version" in f for f in check["findings"])

    def test_stale_exempt_entry_fails(self, repo: Path, monkeypatch) -> None:
        monkeypatch.setitem(voc.SKILL_TOML_EXEMPT, "ghost-skill", "gone")
        check = _check(voc.run_checks(repo), "skill-manifest")
        assert check["status"] == "fail"
        assert any("stale" in f for f in check["findings"])


# ── check: agents-coverage ──────────────────────────────────────────────────


class TestAgentsCoverage:
    def test_valid_repo_passes(self, repo: Path) -> None:
        assert _check(voc.run_checks(repo), "agents-coverage")["status"] == "pass"

    def test_head_missing_from_agents_block_fails(self, repo: Path) -> None:
        cfg = json.loads(voc.strip_jsonc((repo / "opencode.jsonc").read_text()))
        del cfg["agents"]["product-produck"]
        _write(repo / "opencode.jsonc", json.dumps(cfg))
        check = _check(voc.run_checks(repo), "agents-coverage")
        assert check["status"] == "fail"
        assert any("product-produck" in f for f in check["findings"])

    def test_head_missing_runtime_file_fails(self, repo: Path) -> None:
        (repo / ".opencode" / "agents" / "neteng-neet.md").unlink()
        check = _check(voc.run_checks(repo), "agents-coverage")
        assert check["status"] == "fail"
        assert any("neteng-neet" in f for f in check["findings"])

    def test_unmapped_head_profile_fails(self, repo: Path) -> None:
        _write(repo / "profiles" / "INDEX.md", _index_md(extra_profiles=["20-newdept"]))
        check = _check(voc.run_checks(repo), "agents-coverage")
        assert check["status"] == "fail"
        assert any("20-newdept" in f for f in check["findings"])

    def test_stale_head_map_entry_fails(self, repo: Path) -> None:
        # INDEX without the full map → every map entry not in INDEX is stale
        _write(
            repo / "profiles" / "INDEX.md",
            "| `01-ceo` | CEO |\n| `default` | fallback |\n",
        )
        check = _check(voc.run_checks(repo), "agents-coverage")
        assert check["status"] == "fail"
        assert any("stale HEAD_AGENT_MAP" in f for f in check["findings"])

    def test_runtime_override_is_a_note_not_a_failure(self, repo: Path) -> None:
        check = _check(voc.run_checks(repo), "agents-coverage")
        assert check["status"] == "pass"
        assert any("qa-team" in note for note in check["notes"])

    def test_exempt_profile_needs_no_agents_entry(self, repo: Path) -> None:
        cfg = json.loads(voc.strip_jsonc((repo / "opencode.jsonc").read_text()))
        assert "cto" not in cfg["agents"]  # cto is PROFILES_EXEMPT
        assert _check(voc.run_checks(repo), "agents-coverage")["status"] == "pass"


# ── check: permission-lint ──────────────────────────────────────────────────


class TestPermissionLint:
    def test_allowlisted_broad_read_passes(self, repo: Path) -> None:
        assert _check(voc.run_checks(repo), "permission-lint")["status"] == "pass"

    def test_broad_read_in_config_not_allowlisted_fails(self, repo: Path) -> None:
        cfg = json.loads(voc.strip_jsonc((repo / "opencode.jsonc").read_text()))
        cfg["agents"]["product-produck"]["permissions"] = [
            {"action": "read", "resource": "*", "effect": "allow"}
        ]
        _write(repo / "opencode.jsonc", json.dumps(cfg))
        check = _check(voc.run_checks(repo), "permission-lint")
        assert check["status"] == "fail"
        assert any("product-produck" in f for f in check["findings"])

    def test_broad_read_in_frontmatter_not_allowlisted_fails(self, repo: Path) -> None:
        _write(
            repo / ".opencode" / "agents" / "rd-lab.md",
            '---\nname: rd-lab\npermissions:\n  - action: read\n    resource: "*"\n'
            "    effect: allow\n---\n",
        )
        check = _check(voc.run_checks(repo), "permission-lint")
        assert check["status"] == "fail"
        assert any("rd-lab" in f for f in check["findings"])

    def test_scoped_read_passes(self, repo: Path) -> None:
        cfg = json.loads(voc.strip_jsonc((repo / "opencode.jsonc").read_text()))
        cfg["agents"]["rd-lab"]["permissions"] = [
            {"action": "read", "resource": "tools/**", "effect": "allow"}
        ]
        _write(repo / "opencode.jsonc", json.dumps(cfg))
        assert _check(voc.run_checks(repo), "permission-lint")["status"] == "pass"

    def test_frontmatter_parser(self, repo: Path) -> None:
        md = repo / ".opencode" / "agents" / "ceo-turbo.md"
        _write(
            md,
            "---\nname: ceo-turbo\npermissions:\n"
            '  - action: read\n    resource: "*"\n    effect: allow\n'
            '  - action: edit\n    resource: "docs/**"\n    effect: deny\n'
            'color: "#fff"\n---\n',
        )
        rules = voc.parse_frontmatter_permissions(md)
        assert rules == [
            {"action": "read", "resource": "*", "effect": "allow"},
            {"action": "edit", "resource": "docs/**", "effect": "deny"},
        ]


# ── CLI behaviour ───────────────────────────────────────────────────────────


class TestCli:
    def test_strict_zero_on_valid_repo(self, repo: Path, capsys) -> None:
        assert voc.main(["--root", str(repo)]) == 0
        out = capsys.readouterr().out
        assert out.count("[PASS]") == 5
        assert "result: OK" in out

    def test_strict_one_on_broken_repo(self, repo: Path, capsys) -> None:
        cfg = json.loads(voc.strip_jsonc((repo / "opencode.jsonc").read_text()))
        cfg["skills"]["paths"].append("skills/missing")
        _write(repo / "opencode.jsonc", json.dumps(cfg))
        assert voc.main(["--root", str(repo)]) == 1
        assert "[FAIL] skills-paths" in capsys.readouterr().out

    def test_warn_only_exits_zero_and_marks_warn(self, repo: Path, capsys) -> None:
        cfg = json.loads(voc.strip_jsonc((repo / "opencode.jsonc").read_text()))
        cfg["skills"]["paths"].append("skills/missing")
        _write(repo / "opencode.jsonc", json.dumps(cfg))
        assert voc.main(["--root", str(repo), "--warn-only"]) == 0
        out = capsys.readouterr().out
        assert "[WARN] skills-paths" in out
        assert "WARN-ONLY" in out

    def test_json_output(self, repo: Path, capsys) -> None:
        assert voc.main(["--root", str(repo), "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is True
        assert payload["failed"] == []
        assert [c["id"] for c in payload["checks"]] == [
            "skills-paths",
            "skill-id-collisions",
            "skill-manifest",
            "agents-coverage",
            "permission-lint",
        ]

    def test_missing_config_exits_two(self, tmp_path: Path) -> None:
        assert voc.main(["--root", str(tmp_path)]) == 2

    def test_unparsable_config_exits_two(self, tmp_path: Path) -> None:
        _write(tmp_path / "opencode.jsonc", "{ this is not json ")
        assert voc.main(["--root", str(tmp_path)]) == 2


# ── integration: this repository, the exact CI command ──────────────────────


class TestRealRepository:
    def test_validator_is_green_strict(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stdout.count("[PASS]") == 5

    def test_validator_is_green_warn_only(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--warn-only"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def test_real_config_declares_every_head_agent(self) -> None:
        """The five heads that were missing before Wave 2 (plus their peers)."""
        cfg = voc.load_config(REPO_ROOT / "opencode.jsonc")
        for agent_id in (
            "product-produck",
            "neteng-neet",
            "cybersec-sai",
            "psych-jit",
            "rd-lab",
        ):
            assert agent_id in cfg["agents"], f"{agent_id} missing from agents{{}}"

    def test_l1_blocks_are_read_only_where_required(self) -> None:
        cfg = voc.load_config(REPO_ROOT / "opencode.jsonc")
        for agent_id in ("explore", "plan"):
            rules = cfg["agents"][agent_id]["permissions"]
            assert {"action": "edit", "resource": "*", "effect": "deny"} in rules
            assert {"action": "bash", "resource": "*", "effect": "deny"} in rules
            assert {"action": "subagent", "resource": "*", "effect": "deny"} in rules
        build_rules = cfg["agents"]["build"]["permissions"]
        assert {
            "action": "bash",
            "resource": "rm -rf *",
            "effect": "deny",
        } in build_rules

    def test_skills_paths_do_not_reference_missing_dirs(self) -> None:
        cfg = voc.load_config(REPO_ROOT / "opencode.jsonc")
        for rel in cfg["skills"]["paths"]:
            assert (REPO_ROOT / rel).is_dir(), f"dead skills path: {rel}"

    def test_cto_skills_root_precedes_canonical_roots(self) -> None:
        """Last source wins by skill ID — canonical deploy/smoke-test must win."""
        cfg = voc.load_config(REPO_ROOT / "opencode.jsonc")
        paths = cfg["skills"]["paths"]
        assert paths.index("skills/@axis/cto") < paths.index("skills/@axis/engineering")
        assert paths.index("skills/@axis/cto") < paths.index("skills/@axis/qa")

    def test_design_and_marketing_paths_are_gone(self) -> None:
        cfg = voc.load_config(REPO_ROOT / "opencode.jsonc")
        paths = cfg["skills"]["paths"]
        assert "skills/@axis/design" not in paths
        assert "skills/@axis/marketing" not in paths
        assert "skills/@axis/cto" in paths
        assert "skills/@axis" in paths

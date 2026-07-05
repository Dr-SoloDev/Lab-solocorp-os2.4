"""
AO Integration Tests — Full test suite for Agent Orchestration integration.

Tests cover:
  1. Profile ↔ Agent mapping completeness & correctness
  2. Agent adapter registry registration
  3. AO → Bus message flow
  4. Each adapter's build_prompt and parse_response
  5. CLI command integration
  6. Profile hooks (AO checkpoint)
  7. Edge cases & error handling
  8. Reverse mapping consistency
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ===================================================================
# 1. Profile ↔ Agent Mapping Tests
# ===================================================================

PROFILE_TO_AGENT_EXPECTED: dict[str, str] = {
    "01-ceo": "ceo",
    "02-cfo": "orchestrator",
    "03-cmo": "orchestrator",
    "04-orchestrator": "orchestrator",
    "05-architect": "architect",
    "06-product": "orchestrator",
    "07-engineering": "engineering",
    "08-design": "architect",
    "09-ui-designer": "engineering",
    "10-qa": "qa",
    "11-sales": "orchestrator",
    "12-support": "engineering",
    "13-legal": "orchestrator",
    "14-web3": "engineering",
    "15-content-creator": "engineering",
}

EXPECTED_AGENTS = {"ceo", "orchestrator", "architect", "engineering", "qa"}


def test_profile_to_agent_mapping():
    """15 profiles must map to 5 AO agents — complete coverage."""
    from govctl_cli.ao.agents import PROFILE_TO_AGENT

    assert len(PROFILE_TO_AGENT) == 15, (
        f"Expected 15 profiles, got {len(PROFILE_TO_AGENT)}"
    )
    for pid, aid in PROFILE_TO_AGENT_EXPECTED.items():
        assert PROFILE_TO_AGENT[pid] == aid, (
            f"Expected {pid} → {aid}, got {PROFILE_TO_AGENT[pid]}"
        )


def test_all_mapped_agents_are_valid():
    """Every profile must map to one of the 5 valid agents."""
    from govctl_cli.ao.agents import PROFILE_TO_AGENT

    for pid, aid in PROFILE_TO_AGENT.items():
        assert aid in EXPECTED_AGENTS, (
            f"Profile {pid} maps to invalid agent {aid!r}"
        )


def test_get_agent_for_profile():
    from govctl_cli.ao.agents import get_agent_for_profile

    assert get_agent_for_profile("07-engineering") == "engineering"
    assert get_agent_for_profile("10-qa") == "qa"
    assert get_agent_for_profile("01-ceo") == "ceo"


def test_get_agent_for_profile_unknown():
    from govctl_cli.ao.agents import get_agent_for_profile

    with pytest.raises(KeyError, match="Unknown profile"):
        get_agent_for_profile("99-nonexistent")


def test_get_profiles_for_agent():
    from govctl_cli.ao.agents import get_profiles_for_agent

    profiles = get_profiles_for_agent("engineering")
    assert "07-engineering" in profiles
    assert "09-ui-designer" in profiles
    assert "12-support" in profiles
    assert "14-web3" in profiles
    assert "15-content-creator" in profiles


def test_get_profiles_for_agent_unknown():
    from govctl_cli.ao.agents import get_profiles_for_agent

    with pytest.raises(KeyError, match="Unknown agent"):
        get_profiles_for_agent("nonexistent")


# ===================================================================
# 2. Agent Adapter Registry Tests
# ===================================================================


def test_agent_adapter_registry():
    """5 agent adapters must register in REGISTRY."""
    from govctl_cli.ao.adapter import REGISTRY

    assert set(REGISTRY.keys()) == EXPECTED_AGENTS, (
        f"Expected agents {EXPECTED_AGENTS}, got {set(REGISTRY.keys())}"
    )


def test_get_adapter():
    from govctl_cli.ao.adapter import get_adapter

    for aid in EXPECTED_AGENTS:
        adapter = get_adapter(aid)
        assert adapter.agent_id == aid
        assert adapter.display_name


def test_get_adapter_unknown():
    from govctl_cli.ao.adapter import get_adapter

    with pytest.raises(KeyError, match="Unknown agent"):
        get_adapter("nonexistent")


def test_list_agents():
    from govctl_cli.ao import list_agents

    agents = list_agents()
    assert len(agents) == 5
    agent_ids = {a["agent_id"] for a in agents}
    assert agent_ids == EXPECTED_AGENTS
    for a in agents:
        assert "display_name" in a


# ===================================================================
# 3. CEO Adapter Tests
# ===================================================================


def test_ceo_adapter_build_prompt():
    from govctl_cli.ao.agents.ceo import CEOAdapter

    adapter = CEOAdapter()
    context = {
        "question": "Should we migrate to microservices?",
        "project_id": "proj-042",
        "options": ["Keep monolith", "Full migration", "Hybrid approach"],
        "impact_summary": "High effort but better scalability.",
    }
    prompt = adapter.build_prompt(context)

    assert "CEO" in prompt
    assert "Should we migrate to microservices?" in prompt
    assert "Keep monolith" in prompt
    assert "Full migration" in prompt
    assert "Hybrid approach" in prompt
    assert "proj-042" in prompt


def test_ceo_adapter_parse_response():
    from govctl_cli.ao.agents.ceo import CEOAdapter

    adapter = CEOAdapter()
    raw = """
decision: Hybrid approach
rationale: Balance between short-term stability and long-term scalability
risks: Team must maintain both stacks during transition
confidence: high
"""
    result = adapter.parse_response(raw)

    assert result["decision"] == "Hybrid approach"
    assert result["rationale"] != ""
    assert result["confidence"] == "high"


def test_ceo_adapter_full_cycle():
    """CEO adapter build_prompt + parse_response cycle (no CLI needed)."""
    from govctl_cli.ao.agents.ceo import CEOAdapter

    adapter = CEOAdapter()
    context = {
        "question": "Should we adopt Rust for systems programming?",
        "project_id": "proj-043",
    }
    # Test build_prompt
    prompt = adapter.build_prompt(context)
    assert "Rust" in prompt
    assert "proj-043" in prompt

    # Test parse_response with a realistic mock
    mock_raw = """
decision: No, not yet
rationale: Team lacks Rust expertise; migration cost too high
risks: Productivity slowdown during learning curve
confidence: high
"""
    result = adapter.parse_response(mock_raw)
    assert result["decision"] == "No, not yet"
    assert result["confidence"] == "high"


# ===================================================================
# 4. Orchestrator Adapter Tests
# ===================================================================


def test_orchestrator_adapter_build_prompt():
    from govctl_cli.ao.agents.orchestrator import OrchestratorAdapter

    adapter = OrchestratorAdapter()
    context = {
        "task": "Coordinate cross-dept migration to new payment gateway",
        "project_id": "proj-044",
        "involved_depts": ["engineering", "qa", "cfo"],
        "complexity_answers": {
            "scope_impact": True,
            "reversibility": True,
            "resource_commitment": True,
        },
    }
    prompt = adapter.build_prompt(context)

    assert "Orchestrator" in prompt or "Pipeline" in prompt
    assert "cross-dept migration" in prompt
    assert "engineering" in prompt
    assert "qa" in prompt
    assert "cfo" in prompt


def test_orchestrator_complexity_matrix_integration():
    """Orchestrator must integrate with the threshold module."""
    from govctl_cli.ao.agents.orchestrator import OrchestratorAdapter

    adapter = OrchestratorAdapter()
    result = adapter.assess_complexity({
        "scope_impact": True,
        "reversibility": False,
        "resource_commitment": False,
    })

    assert result["score"] == 1
    assert result["threshold"] == "rfc"
    assert result["all_clear"] is False


def test_orchestrator_adapter_parse_response():
    from govctl_cli.ao.agents.orchestrator import OrchestratorAdapter

    adapter = OrchestratorAdapter()
    raw = """
pipeline_plan: Phase 1 — assess, Phase 2 — migrate, Phase 3 — verify
sequence: 1. Assess current gateway, 2. Set up new provider, 3. Run parallel
assigned_to: engineering
governance_path: full_review
estimated_effort: 3 weeks
"""
    result = adapter.parse_response(raw)

    assert result["pipeline_plan"] != ""
    assert result["assigned_to"] == "engineering"
    assert result["governance_path"] == "full_review"
    assert result["estimated_effort"] == "3 weeks"


# ===================================================================
# 5. Architect Adapter Tests
# ===================================================================


def test_architect_adapter_build_prompt():
    from govctl_cli.ao.agents.architect import ArchitectAdapter

    adapter = ArchitectAdapter()
    context = {
        "proposal": "Migrate from REST to GraphQL API layer",
        "project_id": "proj-045",
        "proposal_type": "rfc",
        "constraints": ["Must maintain backward compatibility", "No downtime allowed"],
    }
    prompt = adapter.build_prompt(context)

    assert "Architect" in prompt or "Review" in prompt
    assert "GraphQL" in prompt
    assert "proj-045" in prompt
    assert "backward compatibility" in prompt


def test_architect_adapter_parse_response():
    from govctl_cli.ao.agents.architect import ArchitectAdapter

    adapter = ArchitectAdapter()
    raw = """
verdict: changes_requested
rationale: GraphQL migration introduces schema coupling risks
concerns: Performance impact on existing queries, Caching complexity
adr_required: yes
suggested_adr_title: ADR-014: GraphQL Migration Strategy
"""
    result = adapter.parse_response(raw)

    assert result["verdict"] == "changes_requested"
    assert result["adr_required"] is True
    assert result["suggested_adr_title"] == "ADR-014: GraphQL Migration Strategy"
    assert len(result["concerns"]) == 2


def test_architect_adapter_verdict_accepted():
    from govctl_cli.ao.agents.architect import ArchitectAdapter

    adapter = ArchitectAdapter()
    raw = """
verdict: approved
rationale: No architecture concerns — aligns with existing ADR-008
concerns:
adr_required: no
"""
    result = adapter.parse_response(raw)

    assert result["verdict"] == "approved"
    assert result["adr_required"] is False
    assert result["concerns"] == []


# ===================================================================
# 6. Engineering Adapter Tests
# ===================================================================


def test_engineering_adapter_build_prompt():
    from govctl_cli.ao.agents.engineering import EngineeringAdapter

    adapter = EngineeringAdapter()
    context = {
        "task": "Implement user authentication with OAuth 2.0",
        "project_id": "proj-046",
        "tech_stack": ["FastAPI", "PostgreSQL", "Redis"],
        "acceptance_criteria": [
            "Users can login with Google",
            "Session timeout after 24h",
            "Rate limiting on login endpoint",
        ],
    }
    prompt = adapter.build_prompt(context)

    assert "Engineering" in prompt or "Implementation" in prompt
    assert "OAuth 2.0" in prompt or "OAuth" in prompt
    assert "FastAPI" in prompt
    assert "PostgreSQL" in prompt
    assert "Session timeout" in prompt


def test_engineering_adapter_parse_response():
    from govctl_cli.ao.agents.engineering import EngineeringAdapter

    adapter = EngineeringAdapter()
    raw = """
approach: Implement using FastAPI OAuth middleware with JWT tokens
tasks: Setup auth endpoints, Integrate Google OAuth, Add Redis session store, Add rate limiting
estimated_hours: 40
dependencies: OAuth provider credentials, Redis instance
risks: Token revocation complexity, Rate limiting false positives
"""
    result = adapter.parse_response(raw)

    assert "FastAPI OAuth" in result["approach"]
    assert len(result["tasks"]) == 4
    assert result["estimated_hours"] == "40"
    assert len(result["dependencies"]) == 2
    assert len(result["risks"]) == 2


# ===================================================================
# 7. QA Adapter Tests
# ===================================================================


def test_qa_adapter_build_prompt():
    from govctl_cli.ao.agents.qa import QAAdapter

    adapter = QAAdapter()
    context = {
        "feature": "Payment gateway integration",
        "project_id": "proj-047",
        "test_types": ["unit", "integration", "e2e", "security"],
        "guard_names": ["GUARD-007: Payment Processing", "GUARD-008: PCI Compliance"],
    }
    prompt = adapter.build_prompt(context)

    assert "QA" in prompt or "Test Plan" in prompt
    assert "Payment gateway" in prompt
    assert "security" in prompt
    assert "GUARD-007" in prompt or "GUARD-008" in prompt


def test_qa_adapter_parse_response():
    from govctl_cli.ao.agents.qa import QAAdapter

    adapter = QAAdapter()
    raw = """
test_cases: TC-001: Payment success flow, TC-002: Payment failure handling, TC-003: Refund
coverage_areas: Payment processing, Error handling, Webhook integration
gate_status: pass
recommendation: proceed
evidence_required: Test execution report, Coverage report, Security scan results
"""
    result = adapter.parse_response(raw)

    assert len(result["test_cases"]) == 3
    assert len(result["coverage_areas"]) == 3
    assert result["gate_status"] == "pass"
    assert result["recommendation"] == "proceed"
    assert len(result["evidence_required"]) == 3


def test_qa_adapter_gate_fail():
    from govctl_cli.ao.agents.qa import QAAdapter

    adapter = QAAdapter()
    raw = """
test_cases: TC-001: Login test
coverage_areas: Authentication
gate_status: fail
recommendation: block
evidence_required: Bug report, Failed test logs
"""
    result = adapter.parse_response(raw)

    assert result["gate_status"] == "fail"
    assert result["recommendation"] == "block"


# ===================================================================
# 8. Agent ↔ Bus Message Flow Tests
# ===================================================================


def test_ao_bus_message_flow(tmp_path, monkeypatch):
    """AO_REQUEST → adapter → AO_RESPONSE flow via Central Bus.

    Uses tmp_path to give this test its own isolated queue directory so it
    cannot interfere with — or be interfered by — other tests that use the
    global queue.
    """
    import central_bus.queue as queue_module
    from central_bus import BusMessage
    from govctl_cli.ao.adapter import get_adapter

    # Point the queue module at a private temp directory for this test.
    monkeypatch.setattr(queue_module, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(queue_module, "DEAD_LETTER_DIR", tmp_path / "queue" / "dead_letter")
    (tmp_path / "queue").mkdir(parents=True, exist_ok=True)

    enqueue = queue_module.enqueue
    dequeue = queue_module.dequeue
    requeue = queue_module.requeue

    # 1. Build a bus message for the engineering agent
    msg = BusMessage(
        from_dept="engineering",
        to_dept="engineering",
        type="HANDOFF",
        project_id="proj-ao-test",
        phase="dev",
        payload={"agent_id": "engineering", "task": "Implement feature X"},
        trace_id="trace-ao-001",
        priority="high",
    )

    # 2. Enqueue into isolated queue
    enqueue(msg)

    # 3. Dequeue — isolated queue has exactly our message
    dequeued = dequeue("high")
    assert dequeued is not None
    assert dequeued.id == msg.id, (
        f"Unexpected message id {dequeued.id!r} — expected {msg.id!r}"
    )

    # 4. Resolve agent from payload and execute
    agent_id = dequeued.payload.get("agent_id", "engineering")
    adapter = get_adapter(agent_id)

    context = {
        "task": dequeued.payload.get("task", ""),
        "project_id": dequeued.project_id,
    }
    prompt = adapter.build_prompt(context)
    assert "Implement feature X" in prompt

    # 5. Parse a mock response
    mock_raw = """
approach: Use modular architecture with clear separation
tasks: Setup project structure, Implement core logic, Add tests
estimated_hours: 24
dependencies: Feature spec, Design approval
risks: Scope creep
"""
    result = adapter.parse_response(mock_raw)
    assert len(result["tasks"]) == 3


# ===================================================================
# 9. CLI Command Tests
# ===================================================================


def test_ao_list_via_cli():
    from typer.testing import CliRunner
    from govctl_cli.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["ao", "list"])

    assert result.exit_code == 0, f"CLI failed: {result.stdout}"
    assert "CEO" in result.stdout
    assert "Orchestrator" in result.stdout
    assert "Architect" in result.stdout
    assert "Engineering" in result.stdout
    assert "QA" in result.stdout
    assert "5 registered" in result.stdout or "agents" in result.stdout


def test_ao_list_verbose():
    from typer.testing import CliRunner
    from govctl_cli.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["ao", "list"])

    assert result.exit_code == 0, f"CLI failed: {result.stdout}"
    # The default list shows agent names — verify key ones appear
    assert "CEO" in result.stdout
    assert "Orchestrator" in result.stdout


def test_ao_map_command():
    from typer.testing import CliRunner
    from govctl_cli.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["ao", "map", "07-engineering"])

    assert result.exit_code == 0, f"CLI failed: {result.stdout}"
    assert "07-engineering" in result.stdout
    assert "engineering" in result.stdout  # agent_id


def test_ao_map_unknown_profile():
    from typer.testing import CliRunner
    from govctl_cli.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["ao", "map", "99-nonexistent"])

    assert result.exit_code == 1
    assert "Unknown profile" in result.stdout or "Unknown profile" in result.stderr


def test_ao_run_with_task():
    from typer.testing import CliRunner
    from govctl_cli.cli import app

    runner = CliRunner()
    result = runner.invoke(app, [
        "ao", "run", "engineering",
        "--task", "Implement OAuth",
        "--project", "proj-test",
    ])

    # Should return error because AO CLI not available (not installed),
    # but the command itself should parse correctly (exit 1, not 2)
    assert result.exit_code != 2, f"CLI parser failed: {result.stdout}"
    # exit 0 or 1 is fine for this env (no real AO CLI)


# ===================================================================
# 10. Profile Hooks (AO Checkpoint) Tests
# ===================================================================


def test_add_ao_hook_dry_run(tmp_path):
    from govctl_cli.profile_hooks import add_ao_hook

    # Create a test SOUL.md
    soul_file = tmp_path / "SOUL.md"
    soul_file.write_text("## Rules\n\n- Rule one\n- Rule two\n\n## Context Reference\n")

    result = add_ao_hook(str(soul_file), dry_run=True)
    assert "AO Agent Integration" in result
    assert result.startswith("---")  # It's a diff

    # File should NOT be modified in dry_run
    content = soul_file.read_text()
    assert "AO Agent Integration" not in content


def test_add_ao_hook_already_present(tmp_path):
    from govctl_cli.profile_hooks import add_ao_hook

    soul_file = tmp_path / "SOUL.md"
    soul_file.write_text("## Rules\n\n### AO Agent Integration\n- Already present\n")

    result = add_ao_hook(str(soul_file))
    assert "already present" in result


def test_verify_ao_hooks(tmp_path):
    from govctl_cli.profile_hooks import verify_ao_hooks

    # Create a mock profiles directory
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()

    # Profile with hook
    p1 = profiles_dir / "07-engineering"
    p1.mkdir()
    (p1 / "SOUL.md").write_text("## Rules\n\n### AO Agent Integration\n- something\n")

    # Profile without hook
    p2 = profiles_dir / "02-cfo"
    p2.mkdir()
    (p2 / "SOUL.md").write_text("## Rules\n\nNothing about AO\n")

    report = verify_ao_hooks(str(profiles_dir))

    assert len(report) == 2

    p1_report = [r for r in report if "07-engineering" in r["path"]][0]
    assert p1_report["has_ao_hook"] is True
    assert p1_report["status"] == "ok"

    p2_report = [r for r in report if "02-cfo" in r["path"]][0]
    assert p2_report["has_ao_hook"] is False
    assert p2_report["status"] == "missing"
    # Should detect agent from profile prefix
    assert p2_report["agent_id"] in ("orchestrator",)


# ===================================================================
# 11. Edge Cases & Error Handling
# ===================================================================


def test_empty_context_build_prompt():
    """All adapters must handle empty/minimal context gracefully."""
    from govctl_cli.ao.agents.ceo import CEOAdapter
    from govctl_cli.ao.agents.orchestrator import OrchestratorAdapter
    from govctl_cli.ao.agents.architect import ArchitectAdapter
    from govctl_cli.ao.agents.engineering import EngineeringAdapter
    from govctl_cli.ao.agents.qa import QAAdapter

    for Adapter in [CEOAdapter, OrchestratorAdapter, ArchitectAdapter, EngineeringAdapter, QAAdapter]:
        adapter = Adapter()
        prompt = adapter.build_prompt({})
        assert prompt, f"{Adapter.__name__} returned empty prompt"


def test_empty_raw_parse_response():
    """All adapters must handle empty/malformed raw response."""
    from govctl_cli.ao.agents.ceo import CEOAdapter
    from govctl_cli.ao.agents.orchestrator import OrchestratorAdapter
    from govctl_cli.ao.agents.architect import ArchitectAdapter
    from govctl_cli.ao.agents.engineering import EngineeringAdapter
    from govctl_cli.ao.agents.qa import QAAdapter

    for Adapter in [CEOAdapter, OrchestratorAdapter, ArchitectAdapter, EngineeringAdapter, QAAdapter]:
        adapter = Adapter()
        result = adapter.parse_response("")
        assert isinstance(result, dict)


def test_malformed_response_graceful():
    """Malformed responses must not crash parsers."""
    from govctl_cli.ao.agents.ceo import CEOAdapter

    adapter = CEOAdapter()
    # Random text with no expected fields
    result = adapter.parse_response("Some random text without any key-value pairs")
    assert result["decision"] == ""  # Should be empty, not crash


def test_all_adapters_complete_cycle():
    """Every adapter should complete a full build→parse cycle (no CLI needed)."""
    from govctl_cli.ao.agents.ceo import CEOAdapter
    from govctl_cli.ao.agents.orchestrator import OrchestratorAdapter
    from govctl_cli.ao.agents.architect import ArchitectAdapter
    from govctl_cli.ao.agents.engineering import EngineeringAdapter
    from govctl_cli.ao.agents.qa import QAAdapter

    contexts = {
        CEOAdapter: {"question": "Strategic test?", "project_id": "proj-test"},
        OrchestratorAdapter: {"task": "Orchestration test", "project_id": "proj-test"},
        ArchitectAdapter: {"proposal": "Architecture test", "project_id": "proj-test"},
        EngineeringAdapter: {"task": "Engineering test", "project_id": "proj-test"},
        QAAdapter: {"feature": "QA test", "project_id": "proj-test"},
    }

    for Adapter, ctx in contexts.items():
        adapter = Adapter()
        prompt = adapter.build_prompt(ctx)
        assert prompt, f"{Adapter.__name__}.build_prompt() returned empty"

        raw_mock = "mock_key: mock_value"
        result = adapter.parse_response(raw_mock)
        assert isinstance(result, dict), f"{Adapter.__name__}.parse_response() must return dict"


# ===================================================================
# 12. Reverse Mapping Consistency
# ===================================================================


def test_agenda_to_profiles_consistency():
    """AGENT_TO_PROFILES must be the exact inverse of PROFILE_TO_AGENT."""
    from govctl_cli.ao.agents import PROFILE_TO_AGENT, AGENT_TO_PROFILES

    # Every profile must appear in exactly one agent's list
    all_profiles_in_reverse = set()
    for profiles in AGENT_TO_PROFILES.values():
        all_profiles_in_reverse.update(profiles)

    assert all_profiles_in_reverse == set(PROFILE_TO_AGENT.keys()), (
        "Reverse mapping is missing profiles"
    )

    # Every entry in reverse must map back correctly
    for agent_id, profiles in AGENT_TO_PROFILES.items():
        for pid in profiles:
            assert PROFILE_TO_AGENT[pid] == agent_id, (
                f"Inconsistency: {pid} → {PROFILE_TO_AGENT[pid]} "
                f"but appears in {agent_id}'s list"
            )


def test_all_fifteen_profiles_mapped():
    """All 15 profiles must have an entry."""
    from govctl_cli.ao.agents import PROFILE_TO_AGENT

    expected_ids = {f"{i:02d}-{name}" for i, name in [
        (1, "ceo"), (2, "cfo"), (3, "cmo"), (4, "orchestrator"),
        (5, "architect"), (6, "product"), (7, "engineering"),
        (8, "design"), (9, "ui-designer"), (10, "qa"), (11, "sales"),
        (12, "support"), (13, "legal"), (14, "web3"),
        (15, "content-creator"),
    ]}
    assert set(PROFILE_TO_AGENT.keys()) == expected_ids

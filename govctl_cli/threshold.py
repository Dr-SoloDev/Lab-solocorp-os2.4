"""
Complexity Threshold Engine — Hybrid decision logic for Orchestrator.

RFC-001 defines the Complexity Matrix: 3 binary questions that determine
the governance path for any incoming task.

Usage:
    from govctl_cli.threshold import assess_complexity

    result = assess_complexity({
        "scope_impact": True,
        "reversibility": False,
        "resource_commitment": False,
    })
    # Returns: {"score": 1, "threshold": "rfc", "decision": "RFC required"}
"""

import typer
from typing import Optional

# ---------------------------------------------------------------------------
# Questions definition
# ---------------------------------------------------------------------------
COMPLEXITY_QUESTIONS = [
    {
        "key": "scope_impact",
        "label": "Scope Impact (S)",
        "question": "How many departments / bounded contexts are affected?",
    },
    {
        "key": "reversibility",
        "label": "Reversibility (R)",
        "question": "How difficult / costly is it to reverse this decision once implemented?",
    },
    {
        "key": "resource_commitment",
        "label": "Resource Commitment (C)",
        "question": "How much organizational resource is required?",
    },
]

THRESHOLD_MAP = {
    0: "direct_adr",
    1: "rfc",
    2: "full_review",
    3: "full_review",
}

THRESHOLD_DECISIONS = {
    "direct_adr": "Direct ADR — no RFC needed. Proceed with ADR and execute.",
    "rfc": "RFC required — create RFC, gather feedback, then ADR and execute.",
    "full_review": (
        "Full review required — RFC → Stakeholder review → "
        "ADR → Guard gates (GUARD-001–009) → execute."
    ),
}


def threshold_for_score(score: int) -> str:
    """Map a complexity score (0-3) to a threshold name.

    Args:
        score: Integer 0-3 calculated from the Complexity Matrix.

    Returns:
        One of "direct_adr", "rfc", or "full_review".

    Raises:
        ValueError: If score is outside 0-3.
    """
    if score not in (0, 1, 2, 3):
        raise ValueError(f"Score must be 0-3, got {score!r}")
    return THRESHOLD_MAP[score]


def assess_complexity(answers: dict) -> dict:
    """Evaluate the RFC-001 Complexity Matrix and return a decision.

    Args:
        answers: Dict with keys ``scope_impact``, ``reversibility``,
                 ``resource_commitment`` — each a bool.

    Returns:
        Dict with keys:
          - score (int): 0-3
          - threshold (str): ``direct_adr`` | ``rfc`` | ``full_review``
          - decision (str): Human-readable recommendation
          - details (list[dict]): Per-question breakdown
          - all_clear (bool): True if score == 0
    """
    details = []
    score = 0

    for q in COMPLEXITY_QUESTIONS:
        key = q["key"]
        raw = answers.get(key, False)
        val = bool(raw)
        if val:
            score += 1
        details.append({
            "key": key,
            "label": q["label"],
            "answer": val,
            "weight": 1 if val else 0,
        })

    threshold = threshold_for_score(score)
    decision = THRESHOLD_DECISIONS[threshold]

    return {
        "score": score,
        "threshold": threshold,
        "decision": decision,
        "details": details,
        "all_clear": score == 0,
    }


# ---------------------------------------------------------------------------
# CLI — exposed as a sub-typer on the main ``govctl`` app
# ---------------------------------------------------------------------------

threshold_app = typer.Typer(
    name="threshold",
    help="RFC-001 Complexity Matrix evaluation",
)


@threshold_app.command("assess")
def assess(
    scope_impact: bool = typer.Option(False, "--scope-impact/--no-scope-impact", "-s", help="Cross-department impact?"),
    reversibility: bool = typer.Option(False, "--reversible/--no-reversible", "-r", help="Hard/costly to reverse?"),
    resource_commitment: bool = typer.Option(False, "--resource-commitment/--no-resource-commitment", "-c", help="Significant resource required?"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show per-question details"),
):
    """Assess task complexity using the RFC-001 Complexity Matrix (S + R + C)."""
    answers = {
        "scope_impact": scope_impact,
        "reversibility": reversibility,
        "resource_commitment": resource_commitment,
    }
    result = assess_complexity(answers)

    typer.echo("\n📊 RFC-001 Complexity Matrix Assessment")
    typer.echo("=" * 50)

    if verbose:
        for d in result["details"]:
            mark = "✅" if d["answer"] else "⬜"
            typer.echo(f"  {mark} {d['label']:30s} → {'Yes' if d['answer'] else 'No'}")

    score = result["score"]
    bar = "▓" * score + "░" * (3 - score)
    typer.echo(f"\n  Score:  {score}/3  {bar}")

    # Color-coded threshold badge
    threshold = result["threshold"]
    badge = {"direct_adr": "🟢 DIRECT ADR", "rfc": "🟡 RFC", "full_review": "🔴 FULL REVIEW"}
    typer.echo(f"  Threshold:  {badge.get(threshold, threshold)}")

    if score > 0 and verbose:
        typer.echo(f"\n  📋 {result['decision']}")

    typer.echo()


@threshold_app.command("info")
def info():
    """Show the RFC-001 Complexity Matrix specification."""
    typer.echo("""
RFC-001 — Complexity Matrix
============================
The Complexity Matrix answers 3 binary questions to determine the
governance path for any incoming task:

  ┌──────────────────────────┬─────┬──────────────┐
  │ Question                 │ No  │ Yes          │
  ├──────────────────────────┼─────┼──────────────┤
  │ S — Scope Impact?        │  0  │  +1          │
  │ R — Reversibility?       │  0  │  +1          │
  │ C — Resource Commitment? │  0  │  +1          │
  └──────────────────────────┴─────┴──────────────┘

Score → Threshold:
  0  →  direct_adr   →  ADR only, no RFC needed
  1  →  rfc          →  RFC → ADR
  2-3→  full_review  →  RFC → Stakeholder review → ADR → Guards
""")


@threshold_app.command("batch")
def batch(
    file: str = typer.Option(
        "",
        "--file", "-f",
        help="Path to a JSON file with an array of answer-sets",
    ),
):
    """Assess multiple tasks from a JSON file.

    Expected JSON format:
        [
          {"name": "task A", "scope_impact": true, "reversibility": false, "resource_commitment": false},
          ...
        ]
    """
    import json

    if not file:
        typer.echo("❌ Provide --file path to a JSON array of answer-sets")
        raise typer.Exit(code=1)

    try:
        with open(file) as fh:
            tasks = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        typer.echo(f"❌ Failed to load {file}: {exc}")
        raise typer.Exit(code=1)

    for task in tasks:
        name = task.pop("name", "unnamed")
        result = assess_complexity(task)
        typer.echo(f"  {name:30s} | score {result['score']} → {result['threshold']}")

"""Verification guard commands — real execution engine."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import tomllib
import typer

log = logging.getLogger("govctl.guard")

guard_app = typer.Typer(name="guard", help="Manage verification guards")
GOV_DIR = Path("gov")
AUDIT_DIR = GOV_DIR / "audit"


def _guard_dir() -> Path:
    return GOV_DIR / "guards"


def _load_guard_spec(profile: str = "default") -> dict:
    path = _guard_dir() / f"{profile}.toml"
    if not path.exists():
        raise typer.BadParameter(f"Guard profile '{profile}' not found at {path}")
    with open(path, "rb") as f:
        return tomllib.load(f)


def _load_target_artifact(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return None


def _ensure_audit_dir():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    (AUDIT_DIR / "approval-log").mkdir(parents=True, exist_ok=True)
    (AUDIT_DIR / "reality-checker-log").mkdir(parents=True, exist_ok=True)


# ── Guard Implementations ──────────────────────────────────────────────


def check_guard_001(data: dict) -> list[dict]:
    """Schema Compliance — validate TOML structure against required fields."""
    issues = []
    meta = data.get("metadata", {})
    classification = data.get("classification", {})

    ALLOWED_STATUSES = {"proposed", "draft", "accepted", "deprecated", "superseded"}
    ALLOWED_DOMAINS = {"governance", "documentation", "architecture", "engineering", "product"}
    ALLOWED_IMPACTS = {"low", "medium", "high"}
    ALLOWED_COMPLEXITIES = {"low", "medium", "high"}

    checks = [
        ("metadata.id", bool(meta.get("id"))),
        ("metadata.title", bool(meta.get("title"))),
        ("metadata.status", meta.get("status", "") in ALLOWED_STATUSES),
        ("metadata.author", bool(meta.get("author"))),
        ("metadata.date", bool(re.match(r"^\d{4}-\d{2}-\d{2}$", meta.get("date", "")))),
        ("classification.domain", classification.get("domain", "") in ALLOWED_DOMAINS),
        ("classification.impact", classification.get("impact", "") in ALLOWED_IMPACTS),
        ("classification.complexity", classification.get("complexity", "") in ALLOWED_COMPLEXITIES),
        ("classification.scope", bool(classification.get("scope"))),
    ]

    for field, passed in checks:
        if not passed:
            issues.append({
                "field": field,
                "status": "FAIL",
                "detail": f"{field} is missing or invalid",
            })

    return issues


def check_guard_002(data: dict) -> list[dict]:
    """Bilingual Completeness — check body.en and body.th sections."""
    issues = []

    en = data.get("body", {}).get("en", {})
    th = data.get("body", {}).get("th", {})

    # RFCs use proposal, ADRs use decision — accept either
    en_content_keys = {"summary", "context"}
    th_content_keys = {"summary", "context"}

    # Check decision or proposal
    en_has_content = bool(en.get("decision") or en.get("proposal"))
    th_has_content = bool(th.get("decision") or th.get("proposal"))

    for section in en_content_keys:
        if not en.get(section):
            issues.append({
                "field": f"body.en.{section}",
                "status": "FAIL",
                "detail": f"English section 'body.en.{section}' is missing or empty",
            })

    for section in th_content_keys:
        if not th.get(section):
            issues.append({
                "field": f"body.th.{section}",
                "status": "FAIL",
                "detail": f"Thai section 'body.th.{section}' is missing or empty",
            })

    if not en_has_content:
        issues.append({
            "field": "body.en.decision/proposal",
            "status": "FAIL",
            "detail": "English body must contain either decision or proposal",
        })

    if not th_has_content:
        issues.append({
            "field": "body.th.decision/proposal",
            "status": "FAIL",
            "detail": "Thai body must contain either decision or proposal",
        })

    if not en.get("consequences"):
        issues.append({
            "field": "body.en.consequences",
            "status": "FAIL",
            "detail": "English consequences section is missing or empty",
        })

    if not th.get("consequences"):
        issues.append({
            "field": "body.th.consequences",
            "status": "FAIL",
            "detail": "Thai consequences section is missing or empty",
        })

    return issues


def check_guard_003(data: dict) -> list[dict]:
    """Complexity Score Recorded."""
    issues = []
    classification = data.get("classification", {})
    complexity = classification.get("complexity", "")

    if complexity not in ("low", "medium", "high"):
        issues.append({
            "field": "classification.complexity",
            "status": "FAIL",
            "detail": f"Complexity must be low|medium|high, got '{complexity}'",
        })

    score = data.get("metadata", {}).get("complexity_score")
    if score is not None:
        if not isinstance(score, int) or score < 0 or score > 3:
            issues.append({
                "field": "metadata.complexity_score",
                "status": "FAIL",
                "detail": f"Score must be integer 0-3, got {score!r}",
            })
        else:
            expected = {0: "low", 1: "medium", 2: "high", 3: "high"}
            if expected.get(score) != complexity:
                issues.append({
                    "field": "classification.complexity",
                    "status": "WARN",
                    "detail": f"Complexity '{complexity}' inconsistent with score {score} (expected '{expected.get(score)}')",
                })

    return issues


def check_guard_004(data: dict, current_status: str = "") -> list[dict]:
    """Status Validity & Transition Logic."""
    issues = []
    meta = data.get("metadata", {})
    status = meta.get("status", current_status)

    ALLOWED_STATUSES = {"proposed", "draft", "accepted", "deprecated", "superseded"}
    if status not in ALLOWED_STATUSES:
        issues.append({
            "field": "metadata.status",
            "status": "FAIL",
            "detail": f"Status '{status}' not in allowed set: {', '.join(sorted(ALLOWED_STATUSES))}",
        })

    if status == "superseded":
        refs = data.get("footer", {}).get("references", [])
        if not refs:
            issues.append({
                "field": "footer.references",
                "status": "FAIL",
                "detail": "Superseded artifacts must reference the superseding ADR/RFC",
            })

    if status == "deprecated":
        refs = data.get("footer", {}).get("references", [])
        if not refs:
            issues.append({
                "field": "footer.references",
                "status": "WARN",
                "detail": "Deprecated artifacts should reference deprecation rationale or replacement",
            })

    return issues


def check_guard_005(data: dict) -> list[dict]:
    """Review Date Compliance."""
    issues = []
    footer = data.get("footer", {})
    meta = data.get("metadata", {})
    review_date_str = footer.get("review_date", "")

    if not review_date_str:
        issues.append({
            "field": "footer.review_date",
            "status": "FAIL",
            "detail": "review_date is missing",
        })
        return issues

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", review_date_str):
        issues.append({
            "field": "footer.review_date",
            "status": "FAIL",
            "detail": f"review_date '{review_date_str}' is not valid ISO date (YYYY-MM-DD)",
        })
        return issues

    try:
        review_date = datetime.strptime(review_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        created_str = meta.get("date", "")
        if created_str and re.match(r"^\d{4}-\d{2}-\d{2}$", created_str):
            created_date = datetime.strptime(created_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            delta = (review_date - created_date).days
            if delta > 90:
                issues.append({
                    "field": "footer.review_date",
                    "status": "WARN",
                    "detail": f"review_date is {delta} days after created (max 90 days)",
                })

        now = datetime.now(timezone.utc)
        if review_date < now:
            days_overdue = (now - review_date).days
            if days_overdue > 30:
                issues.append({
                    "field": "footer.review_date",
                    "status": "WARN",
                    "detail": f"review_date is {days_overdue} days overdue (HIGH)",
                })
            elif days_overdue > 0:
                issues.append({
                    "field": "footer.review_date",
                    "status": "WARN",
                    "detail": f"review_date is {days_overdue} days overdue",
                })

    except ValueError as exc:
        issues.append({
            "field": "footer.review_date",
            "status": "FAIL",
            "detail": f"Invalid date: {exc}",
        })

    return issues


def check_guard_006(data: dict) -> list[dict]:
    """Cross-Reference Integrity."""
    issues = []
    footer = data.get("footer", {})
    references = footer.get("references", [])

    if not references:
        return issues

    for ref in references:
        ref = ref.strip()
        if ref.startswith("ADR-"):
            adr_path = GOV_DIR / "adr" / f"{ref}.toml"
            if not adr_path.exists():
                issues.append({
                    "field": f"footer.references -> {ref}",
                    "status": "FAIL",
                    "detail": f"Reference {ref} -> {adr_path} does not exist",
                })
        elif ref.startswith("RFC-"):
            rfc_path = GOV_DIR / "rfc" / f"{ref}.toml"
            if not rfc_path.exists():
                issues.append({
                    "field": f"footer.references -> {ref}",
                    "status": "FAIL",
                    "detail": f"Reference {ref} -> {rfc_path} does not exist",
                })

    return issues


def check_guard_009(data: dict) -> list[dict]:
    """Reality Checker — automated internal-consistency pre-checks before human sign-off."""
    issues = []
    meta = data.get("metadata", {})
    classification = data.get("classification", {})
    footer = data.get("footer", {})

    # Artifact ID must match ADR-NNN or RFC-NNN
    artifact_id = meta.get("id", "")
    if artifact_id and not re.match(r"^(ADR|RFC)-\d{3}$", artifact_id):
        issues.append({
            "field": "metadata.id",
            "status": "WARN",
            "detail": f"ID '{artifact_id}' does not match expected pattern ADR-NNN or RFC-NNN",
        })

    # review_date must not be earlier than created date
    created_str = meta.get("date", "") or meta.get("created", "")
    review_str = footer.get("review_date", "")
    if created_str and review_str:
        try:
            created = datetime.strptime(created_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            review = datetime.strptime(review_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if review < created:
                issues.append({
                    "field": "footer.review_date",
                    "status": "FAIL",
                    "detail": (
                        f"review_date ({review_str}) is before created date ({created_str})"
                    ),
                })
        except ValueError:
            pass  # Date format errors are already caught by GUARD-005

    # scope=organization-wide with impact=low is suspicious
    scope = classification.get("scope", "")
    impact = classification.get("impact", "")
    if scope == "organization-wide" and impact == "low":
        issues.append({
            "field": "classification.impact",
            "status": "WARN",
            "detail": (
                "scope='organization-wide' with impact='low' is unusual — "
                "verify this is intentional"
            ),
        })

    # No placeholder markers in critical metadata fields.
    # Use word-boundary regex so legitimate prose (e.g. "must not contain placeholder text")
    # is not flagged — only standalone markers like TODO, TBD, FIXME are caught.
    PLACEHOLDER_RE = re.compile(
        r"\b(todo|tbd|fixme|lorem\s+ipsum|fill\s+in)\b", re.IGNORECASE
    )
    for field_key in ("title", "author"):
        val = meta.get(field_key, "")
        if PLACEHOLDER_RE.search(val):
            issues.append({
                "field": f"metadata.{field_key}",
                "status": "FAIL",
                "detail": (
                    f"metadata.{field_key} contains placeholder text: "
                    f"'{meta.get(field_key)}'"
                ),
            })

    # No placeholder markers in body sections
    for lang in ("en", "th"):
        body_lang = data.get("body", {}).get(lang, {})
        for section in ("summary", "context", "decision", "proposal", "consequences"):
            val = body_lang.get(section, "")
            if val and PLACEHOLDER_RE.search(val):
                issues.append({
                    "field": f"body.{lang}.{section}",
                    "status": "WARN",
                    "detail": f"body.{lang}.{section} may contain placeholder text",
                })

    return issues


GUARD_CHECKERS = {
    "GUARD-001": check_guard_001,
    "GUARD-002": check_guard_002,
    "GUARD-003": check_guard_003,
    "GUARD-004": check_guard_004,
    "GUARD-005": check_guard_005,
    "GUARD-006": check_guard_006,
    "GUARD-009": check_guard_009,
}


# ── CLI Commands ───────────────────────────────────────────────────────


@guard_app.command()
def list():
    """List all guard profiles and their guards."""
    if not _guard_dir().exists():
        typer.echo("No guards directory found")
        return
    profiles = sorted(_guard_dir().glob("*.toml"))
    if not profiles:
        typer.echo("No guard profiles found")
        return
    for p in profiles:
        data = _load_guard_spec(p.stem)
        guard_list = data.get("guards", [])
        meta = data.get("metadata", {})
        guard_id = meta.get("id", p.stem)
        typer.echo(f"\n{'=' * 50}")
        typer.echo(f"  {guard_id:20s} | {meta.get('title', '')}")
        typer.echo(f"  Status: {meta.get('status', '')} | Version: {meta.get('version', '')}")
        typer.echo(f"  Applies to: {', '.join(data.get('metadata', {}).get('applies_to', ['*']))}")
        typer.echo(f"{'=' * 50}")
        for g in guard_list:
            gid = g.get("id", "?")
            gname = g.get("name", "")
            gtype = g.get("type", "?")
            gsev = g.get("severity", "?")
            icon = {"automated": "🤖", "manual": "👤"}
            typer.echo(f"  {icon.get(gtype, '❓')} {gid:20s} | {gname:30s} | {gtype:10s} | {gsev}")
    typer.echo()


@guard_app.command()
def run(
    profile: str = typer.Option("default", "--profile", "-p", help="Guard profile to run"),
    target: str = typer.Option("", "--target", "-t", help="Target artifact path (TOML file)"),
):
    """Run verification guards against a target artifact."""
    spec = _load_guard_spec(profile)
    guard_list = spec.get("guards", [])
    exec_order = spec.get("execution", {}).get("order", [])
    meta = spec.get("metadata", {})

    if not target:
        typer.echo("❌ --target/-t is required (path to TOML artifact)")
        raise typer.Exit(code=1)

    target_path = Path(target)
    artifact = _load_target_artifact(target_path)
    if artifact is None:
        typer.echo(f"❌ Cannot load artifact: {target}")
        raise typer.Exit(code=1)

    _ensure_audit_dir()

    guards_by_id = {g["id"]: g for g in guard_list}
    results = []
    failed = 0
    warned = 0
    blocked = False

    typer.echo(f"\n{'=' * 55}")
    typer.echo(f"  🔍 Guard Profile: {profile} ({meta.get('id', '')})")
    typer.echo(f"  📄 Target: {target_path}")
    typer.echo(f"{'=' * 55}\n")

    for gid in exec_order:
        guard = guards_by_id.get(gid)
        if not guard:
            typer.echo(f"  ⚠️  Guard {gid} defined in execution order but not found in spec")
            continue

        gtype = guard.get("type", "automated")
        gname = guard.get("name", gid)
        severity = guard.get("severity", "warning")

        typer.echo(f"  ── [{gid}] {gname} ({gtype}) ──")

        if gtype == "automated":
            checker = GUARD_CHECKERS.get(gid)
            if checker:
                issues = checker(artifact)
            else:
                issues = [{"field": "_engine", "status": "WARN", "detail": "No checker implemented for this guard"}]
        else:
            # Run automated pre-checks if a checker exists for this manual guard,
            # then append the human-approval requirement on top.
            checker = GUARD_CHECKERS.get(gid)
            if checker:
                issues = checker(artifact)
                issues.append({
                    "field": "_manual",
                    "status": "PENDING",
                    "detail": "Manual sign-off still required — run `govctl guard approve`",
                })
            else:
                issues = [
                    {"field": "_manual", "status": "PENDING", "detail": "Manual guard — requires human approval"}
                ]

        for issue in issues:
            status = issue["status"]
            icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "PENDING": "⏳"}.get(status, "❓")
            if status == "FAIL":
                failed += 1
            elif status == "WARN":
                warned += 1
            typer.echo(f"    {icon} {issue['field']:35s} | {issue['detail']}")

        if not issues:
            typer.echo(f"    ✅ All checks passed")

        results.append({
            "guard_id": gid,
            "name": gname,
            "type": gtype,
            "severity": severity,
            "issues": issues,
            "passed": all(i["status"] not in ("FAIL",) for i in issues) if issues else True,
        })

        blocked = blocked or any(
            i["status"] == "FAIL" and severity == "blocking"
            for i in issues
        )

        typer.echo()

    # Summary
    typer.echo(f"{'=' * 55}")
    total = len(exec_order)
    passed_count = sum(1 for r in results if r["passed"])
    typer.echo(f"  Results: {passed_count}/{total} guards passed")
    if failed:
        typer.echo(f"  ❌ {failed} check(s) FAILED")
    if warned:
        typer.echo(f"  ⚠️  {warned} warning(s)")
    if blocked:
        typer.echo(f"  🚫 Outcome: BLOCKED — blocking issues found")
        typer.echo(f"  {'=' * 55}")
        raise typer.Exit(code=1)
    else:
        typer.echo(f"  ✅ Outcome: PASSED")
        typer.echo(f"  {'=' * 55}")


@guard_app.command()
def check(
    guard_id: str = typer.Argument(..., help="Guard ID to run (e.g. GUARD-001)"),
    target: str = typer.Option("", "--target", "-t", help="Target artifact path"),
    profile: str = typer.Option("default", "--profile", "-p", help="Guard profile"),
):
    """Run a single guard check against a target artifact."""
    spec = _load_guard_spec(profile)
    guards_by_id = {g["id"]: g for g in spec.get("guards", [])}

    guard = guards_by_id.get(guard_id)
    if not guard:
        typer.echo(f"❌ Guard {guard_id} not found in profile '{profile}'")
        raise typer.Exit(code=1)

    if not target:
        typer.echo("❌ --target/-t is required")
        raise typer.Exit(code=1)

    target_path = Path(target)
    artifact = _load_target_artifact(target_path)
    if artifact is None:
        typer.echo(f"❌ Cannot load artifact: {target}")
        raise typer.Exit(code=1)

    typer.echo(f"\n🔍 [{guard_id}] {guard.get('name', '')} — {guard.get('type', '')}")

    if guard.get("type") == "automated":
        checker = GUARD_CHECKERS.get(guard_id)
        if checker:
            issues = checker(artifact)
        else:
            issues = [{"field": "_engine", "status": "WARN", "detail": "No checker implemented"}]
    else:
        checker = GUARD_CHECKERS.get(guard_id)
        if checker:
            issues = checker(artifact)
            issues.append({
                "field": "_manual",
                "status": "PENDING",
                "detail": "Manual sign-off still required — run `govctl guard approve`",
            })
        else:
            issues = [{"field": "_manual", "status": "PENDING", "detail": "Manual guard — requires human approval"}]

    for issue in issues:
        status = issue["status"]
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "PENDING": "⏳"}.get(status, "❓")
        typer.echo(f"  {icon} {issue['field']:35s} | {issue['detail']}")

    if not issues:
        typer.echo("  ✅ All checks passed")

    any_fail = any(i["status"] == "FAIL" for i in issues)
    if any_fail:
        raise typer.Exit(code=1)


@guard_app.command()
def approve(
    guard_id: str = typer.Argument(..., help="Manual guard ID to approve (GUARD-007, GUARD-008, GUARD-009)"),
    target: str = typer.Option("", "--target", "-t", help="Target artifact path"),
    approver: str = typer.Option("", "--approver", "-a", help="Name of the approver"),
    profile: str = typer.Option("default", "--profile", "-p", help="Guard profile"),
):
    """Approve a manual guard (Stakeholder Sign-off, Cross-Dept Notification, Reality Checker)."""
    spec = _load_guard_spec(profile)
    guards_by_id = {g["id"]: g for g in spec.get("guards", [])}

    guard = guards_by_id.get(guard_id)
    if not guard:
        typer.echo(f"❌ Guard {guard_id} not found in profile '{profile}'")
        raise typer.Exit(code=1)

    if guard.get("type") != "manual":
        typer.echo(f"❌ Guard {guard_id} is not a manual guard")
        raise typer.Exit(code=1)

    if not approver:
        typer.echo("❌ --approver/-a is required for manual approval")
        raise typer.Exit(code=1)

    _ensure_audit_dir()
    approval_log = AUDIT_DIR / "approval-log" / f"{guard_id}_{Path(target).stem}.json"
    record = {
        "guard_id": guard_id,
        "guard_name": guard.get("name", ""),
        "target": str(target),
        "approver": approver,
        "status": "approved",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    approval_log.write_text(json.dumps(record, indent=2))

    typer.echo(f"\n✅ [{guard_id}] {guard.get('name', '')} — APPROVED by {approver}")
    typer.echo(f"   Approval recorded: {approval_log}")


@guard_app.command()
def reject(
    guard_id: str = typer.Argument(..., help="Manual guard ID to reject"),
    target: str = typer.Option("", "--target", "-t", help="Target artifact path"),
    approver: str = typer.Option("", "--approver", "-a", help="Name of the approver"),
    reason: str = typer.Option("", "--reason", "-r", help="Rejection reason"),
    profile: str = typer.Option("default", "--profile", "-p", help="Guard profile"),
):
    """Reject a manual guard."""
    spec = _load_guard_spec(profile)
    guards_by_id = {g["id"]: g for g in spec.get("guards", [])}

    guard = guards_by_id.get(guard_id)
    if not guard:
        typer.echo(f"❌ Guard {guard_id} not found in profile '{profile}'")
        raise typer.Exit(code=1)

    if guard.get("type") != "manual":
        typer.echo(f"❌ Guard {guard_id} is not a manual guard")
        raise typer.Exit(code=1)

    if not approver:
        typer.echo("❌ --approver/-a is required")
        raise typer.Exit(code=1)

    _ensure_audit_dir()
    approval_log = AUDIT_DIR / "approval-log" / f"{guard_id}_{Path(target).stem}.json"
    record = {
        "guard_id": guard_id,
        "guard_name": guard.get("name", ""),
        "target": str(target),
        "approver": approver,
        "status": "rejected",
        "reason": reason or "No reason provided",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    approval_log.write_text(json.dumps(record, indent=2))

    typer.echo(f"\n❌ [{guard_id}] {guard.get('name', '')} — REJECTED by {approver}")
    typer.echo(f"   Reason: {reason or 'No reason provided'}")
    raise typer.Exit(code=1)


@guard_app.command()
def status(
    target: str = typer.Argument(..., help="Target artifact path"),
    profile: str = typer.Option("default", "--profile", "-p", help="Guard profile"),
):
    """Show guard approval status for a target artifact."""
    spec = _load_guard_spec(profile)
    guards = spec.get("guards", [])

    _ensure_audit_dir()
    target_stem = Path(target).stem

    typer.echo(f"\n📊 Guard Status for: {target}")
    typer.echo("=" * 50)

    for g in guards:
        gid = g["id"]
        gtype = g.get("type", "?")
        approval_log = AUDIT_DIR / "approval-log" / f"{gid}_{target_stem}.json"
        status_text = "✅ APPROVED" if approval_log.exists() else "⏳ PENDING"

        if approval_log.exists():
            record = json.loads(approval_log.read_text())
            status_text = f"✅ {record.get('status', 'approved').upper()} by {record.get('approver', '?')}"

        typer.echo(f"  {status_text}  {gid:20s} | {g['name']:30s} ({gtype})")

    typer.echo()

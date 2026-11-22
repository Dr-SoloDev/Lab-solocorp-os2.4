"""CK-NEXUS soul adapter (D2 showcase).

Maps 7 CK-NEXUS roles to SoloCorp department format.
Pure stdlib, no LLM, no network, no secrets.
"""

import hashlib
import json
from datetime import datetime, timezone

CANONICAL_7 = [
    "lead_orchestrator",
    "specialist_alpha",
    "specialist_beta",
    "specialist_gamma",
    "specialist_delta",
    "specialist_epsilon",
    "debate_synthesizer",
]

FORBIDDEN_TOKENS = ("grant", "permission", "execution", "authority")
EVIDENCE_FIELDS = ("subject_sha", "timestamp", "source")


def _norm_role(role):
    """Normalize one role entry to a plain name string."""
    if isinstance(role, dict):
        return str(role.get("name", role.get("role", ""))).strip()
    return str(role).strip()


def adapt(roles7: list) -> dict:
    """Convert 7 CK-NEXUS roles to SoloCorp dept format."""
    names = [_norm_role(r) for r in (roles7 or [])]
    if len(names) != 7:
        raise ValueError(f"expected 7 roles, got {len(names)}: {names}")
    if len(set(names)) != 7:
        raise ValueError(f"roles must be unique: {names}")
    head_name = names[0]
    specialist_names = names[1:6]
    synthesizer = names[6]
    digest = hashlib.sha256(",".join(names).encode()).hexdigest()[:16]
    specialists = [
        {"name": n, "bus_role": f"specialist.{i + 1}"}
        for i, n in enumerate(specialist_names)
    ]
    return {
        "dept_id": "cknexus-showcase",
        "head": {"name": head_name, "bus_role": "head.orchestrator"},
        "specialists": specialists,
        "synthesizer": {"name": synthesizer, "bus_role": "debate.synth"},
        "bus_topic": f"bus.showcase.cknexus.{digest}",
        "evidence": {
            "subject_sha": digest,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "cknexus_soul_adapter.adapt",
        },
    }


def _find_forbidden(obj, path="$"):
    """Recursively collect forbidden-token hits as error strings."""
    hits = []
    if isinstance(obj, dict):
        for key, val in obj.items():
            low_key = str(key).lower()
            for tok in FORBIDDEN_TOKENS:
                if tok in low_key:
                    hits.append(f"{path}.{key}: forbidden key token '{tok}'")
            hits.extend(_find_forbidden(val, f"{path}.{key}"))
    elif isinstance(obj, (list, tuple)):
        for idx, item in enumerate(obj):
            hits.extend(_find_forbidden(item, f"{path}[{idx}]"))
    elif isinstance(obj, str):
        low_val = obj.lower()
        for tok in FORBIDDEN_TOKENS:
            if tok in low_val:
                hits.append(f"{path}: forbidden value token '{tok}'")
    return hits


def validate(mapping: dict) -> tuple:
    """Check no excess authority and evidence fields complete."""
    errors = []
    if not isinstance(mapping, dict):
        return False, ["mapping must be a dict"]
    for field in ("dept_id", "head", "specialists", "bus_topic"):
        if field not in mapping:
            errors.append(f"missing field: {field}")
    errors.extend(_find_forbidden(mapping))
    evidence = mapping.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("missing field: evidence")
    else:
        for field in EVIDENCE_FIELDS:
            if not evidence.get(field):
                errors.append(f"missing evidence field: {field}")
    return (len(errors) == 0, errors)


def _demo_roles():
    """Return a copy of the canonical 7 demo roles."""
    return list(CANONICAL_7)


if __name__ == "__main__":
    demo = adapt(_demo_roles())
    ok, errs = validate(demo)
    print(json.dumps({"mapping": demo, "valid": ok, "errors": errs}, indent=2))

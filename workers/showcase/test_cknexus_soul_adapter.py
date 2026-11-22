"""Pytest for cknexus_soul_adapter (D2 showcase)."""

import json
import subprocess
import sys

from workers.showcase.cknexus_soul_adapter import (
    CANONICAL_7,
    adapt,
    validate,
)


def test_adapt_maps_all_seven_roles():
    mapping = adapt(list(CANONICAL_7))
    assert mapping["dept_id"] == "cknexus-showcase"
    assert mapping["head"]["name"] == "lead_orchestrator"
    assert len(mapping["specialists"]) == 5
    got = [mapping["head"]["name"]]
    got += [s["name"] for s in mapping["specialists"]]
    got += [mapping["synthesizer"]["name"]]
    assert got == list(CANONICAL_7)
    assert mapping["bus_topic"].startswith("bus.showcase.cknexus.")


def test_adapt_rejects_wrong_count():
    try:
        adapt(["only-one"])
    except ValueError as exc:
        assert "expected 7 roles" in str(exc)
    else:
        raise AssertionError("adapt should raise on wrong count")


def test_validate_accepts_clean_mapping():
    ok, errors = validate(adapt(list(CANONICAL_7)))
    assert ok is True
    assert errors == []


def test_validate_catches_excess_permission():
    mapping = adapt(list(CANONICAL_7))
    mapping["specialists"][0]["grant"] = "execution authority"
    ok, errors = validate(mapping)
    assert ok is False
    assert any("forbidden" in e for e in errors)


def test_validate_catches_missing_evidence():
    mapping = adapt(list(CANONICAL_7))
    del mapping["evidence"]["subject_sha"]
    ok, errors = validate(mapping)
    assert ok is False
    assert any("subject_sha" in e for e in errors)


def test_demo_main_does_not_crash():
    proc = subprocess.run(
        [sys.executable, "-m", "workers.showcase.cknexus_soul_adapter"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["valid"] is True
    assert payload["mapping"]["dept_id"] == "cknexus-showcase"

from __future__ import annotations

import hashlib
import json

from axis_mcp.departments import legal_mcp


def _isolate(tmp_path, monkeypatch):
    vault = tmp_path / "legal_vault" / "reviews"
    vault.mkdir(parents=True)
    monkeypatch.setattr(legal_mcp, "ROOT", tmp_path)
    monkeypatch.setattr(legal_mcp, "REVIEWS_ROOT", vault)
    return vault


def test_info_requires_human_review():
    d = json.loads(legal_mcp.legal_department_info())
    assert d["status"] == "ok" and d["department"] == "legal"
    assert d["head"]["id"] == "legal-tulya"
    assert len(d["specialists"]) == 3
    assert d["requires_human_review"] is True


def test_list_matters_limit():
    d = json.loads(legal_mcp.legal_list_matters())
    assert d["count"] == 3 and d["requires_human_review"] is True
    assert json.loads(legal_mcp.legal_list_matters(limit=1))["count"] == 1


def test_create_review_never_approves(tmp_path, monkeypatch):
    vault = _isolate(tmp_path, monkeypatch)
    r = json.loads(legal_mcp.legal_create_review("NDA Acme", "review scope"))
    assert r["status"] == "ok" and r["requires_human_review"] is True
    p = vault / "REVIEW-nda-acme.md"
    assert p.exists()
    body = p.read_text(encoding="utf-8")
    assert "AWAITING HUMAN REVIEW" in body and "approv" not in body.lower().replace(
        "never approves", ""
    )
    assert r["sha256"] == hashlib.sha256(body.encode()).hexdigest()


def test_create_review_invalid_and_traversal(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    r = json.loads(legal_mcp.legal_create_review("!!!"))
    assert r["status"] == "error" and r["error"] == "invalid_title"


def test_check_compliance_all_human(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    r = json.loads(legal_mcp.legal_check_compliance("soc2, iso27001"))
    assert r["status"] == "ok" and r["count"] == 2
    assert all(x["verdict"] == "requires_human_review" for x in r["checklist"])
    e = json.loads(legal_mcp.legal_check_compliance("  "))
    assert e["error"] == "empty_items"

from __future__ import annotations

import hashlib
import json

from axis_mcp.departments import product_mcp


def _isolate(tmp_path, monkeypatch):
    drafts = tmp_path / "docs" / "prds" / "drafts"
    drafts.mkdir(parents=True)
    monkeypatch.setattr(product_mcp, "ROOT", tmp_path)
    monkeypatch.setattr(product_mcp, "DRAFTS_ROOT", drafts)
    return drafts


def test_info_head_and_specialists():
    d = json.loads(product_mcp.product_department_info())
    assert d["status"] == "ok" and d["department"] == "product"
    assert d["head"]["id"] == "product-produck"
    assert len(d["specialists"]) == 3
    assert d["data_root"] == "docs/prds/drafts/"


def test_list_features_limit():
    d = json.loads(product_mcp.product_list_features())
    assert d["count"] == 3 and len(d["features"]) == 3
    d2 = json.loads(product_mcp.product_list_features(limit=2))
    assert d2["count"] == 2


def test_create_prd_writes_template(tmp_path, monkeypatch):
    drafts = _isolate(tmp_path, monkeypatch)
    r = json.loads(product_mcp.product_create_prd("App Shell", "Need one CEO home"))
    assert r["status"] == "ok"
    p = drafts / "PRD-app-shell.md"
    assert p.exists()
    body = p.read_text(encoding="utf-8")
    assert "# PRD: App Shell" in body and "## Problem Statement" in body
    assert "### Must Have (P0)" in body and "## Out of Scope" in body
    assert r["sha256"] == hashlib.sha256(body.encode()).hexdigest()
    assert r["path"].endswith("PRD-app-shell.md")


def test_create_prd_invalid_title():
    r = json.loads(product_mcp.product_create_prd("!!!"))
    assert r["status"] == "error" and r["error"] == "invalid_title"


def test_prioritize_rank_and_empty():
    r = json.loads(product_mcp.product_prioritize("login, export, pdf"))
    assert r["status"] == "ok" and r["count"] == 3
    assert [x["rank"] for x in r["ranked"]] == [1, 2, 3]
    assert r["ranked"][0]["item"] == "login"
    e = json.loads(product_mcp.product_prioritize("   "))
    assert e["status"] == "error" and e["error"] == "empty_items"

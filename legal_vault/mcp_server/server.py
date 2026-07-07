"""
Legal Vault MCP Server
======================
Serve SoloCorp legal document templates via MCP protocol.

Run (stdio, for Claude/OpenCode MCP integration):
    python legal_vault/mcp_server/server.py
"""
from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .loader import (
    TEMPLATES_DIR,
    get_document_content,
    get_us_reference,
    get_usage_guide,
    load_all_documents,
    to_summary,
)
from .models import COUNSEL_WARNING, DocumentFull
from .search import search as _search

mcp = FastMCP(
    name="legal-vault",
    description=(
        "SoloCorp legal document repository — Thai-adapted templates: "
        "NDA (mutual/one-way), Consulting Agreement, PDPA Privacy Policy, "
        "Customer Agreement, ToS, IP Assignment, Advisor Agreement (FAST). "
        "Always check 'requires_external_counsel' before using any document."
    ),
)


@mcp.tool()
def list_documents(
    status_filter: str = "approved",
    doc_type_filter: str = "all",
) -> dict:
    """
    List all legal document templates in the SoloCorp vault.
    Returns metadata summaries. Use status_filter='all' to include drafts.
    """
    docs = load_all_documents()
    summaries = []
    for meta, _ in docs:
        if status_filter != "all" and meta.status != status_filter:
            continue
        if doc_type_filter != "all" and meta.doc_type != doc_type_filter:
            continue
        summaries.append(to_summary(meta).model_dump())
    return {"documents": summaries, "total": len(summaries)}


@mcp.tool()
def search_documents(
    query: str,
    use_case: str | None = None,
    framework: str | None = None,
    jurisdiction: str | None = None,
    status_filter: str = "approved",
) -> dict:
    """
    Search legal documents by keyword, use case, or framework.
    Searches title, use_cases, frameworks, and document body.
    Supports Thai and English queries.
    """
    results = _search(
        query=query,
        use_case=use_case,
        framework=framework,
        jurisdiction=jurisdiction,
        status_filter=status_filter,
    )
    interpreted = f"query='{query}'"
    if use_case:
        interpreted += f", use_case='{use_case}'"
    if framework:
        interpreted += f", framework='{framework}'"
    if jurisdiction:
        interpreted += f", jurisdiction='{jurisdiction}'"
    return {"results": results, "total": len(results), "query_interpreted": interpreted}


@mcp.tool()
def get_document(
    doc_id: str,
    include_usage_guide: bool = True,
    include_us_reference: bool = False,
) -> dict:
    """
    Retrieve a specific legal document template by ID.
    Returns full Thai template text plus metadata.
    IMPORTANT: Check 'counsel_warning' — if non-null, external legal review is required.
    """
    doc_dir = TEMPLATES_DIR / doc_id
    if not doc_dir.exists() or not doc_dir.is_dir():
        return {
            "error": f"Document '{doc_id}' not found. Use list_documents to see valid IDs."
        }
    docs = load_all_documents()
    meta = next((m for m, d in docs if d == doc_dir), None)
    if meta is None:
        return {"error": f"Could not parse metadata for '{doc_id}'"}

    result = DocumentFull(
        id=meta.id,
        metadata=meta,
        content_th=get_document_content(doc_dir),
        usage_guide=get_usage_guide(doc_dir) if include_usage_guide else None,
        content_us_ref=get_us_reference(doc_dir) if include_us_reference else None,
        counsel_warning=COUNSEL_WARNING if meta.requires_external_counsel else None,
    )
    return result.model_dump()


if __name__ == "__main__":
    mcp.run()

"""Keyword + metadata search across loaded documents."""
from __future__ import annotations

from pathlib import Path

from .loader import get_document_content, load_all_documents, to_summary
from .models import DocumentMeta


def _text_match(query: str, meta: DocumentMeta, body: str) -> tuple[bool, str]:
    q = query.lower()
    if q in meta.title.lower() or q in meta.title_en.lower():
        return True, "title"
    for uc in meta.use_cases:
        if q in uc.lower():
            return True, "use_case"
    for fw in meta.frameworks:
        if q in fw.lower():
            return True, "framework"
    if q in body.lower():
        return True, "body_keyword"
    return False, ""


def search(
    query: str,
    use_case: str | None = None,
    framework: str | None = None,
    jurisdiction: str | None = None,
    status_filter: str = "approved",
) -> list[dict]:
    docs = load_all_documents()
    results = []
    for meta, doc_dir in docs:
        if status_filter != "all" and meta.status != status_filter:
            continue
        if use_case and use_case not in meta.use_cases:
            continue
        if framework and framework not in meta.frameworks:
            continue
        if jurisdiction and meta.jurisdiction != jurisdiction:
            continue
        body = get_document_content(doc_dir)
        matched, reason = _text_match(query, meta, body)
        if matched:
            summary = to_summary(meta)
            results.append({**summary.model_dump(), "match_reason": reason})
    return results

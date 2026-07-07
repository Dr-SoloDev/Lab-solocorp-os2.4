"""Filesystem loader — reads legal_vault/templates/ and parses frontmatter."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import frontmatter

from .models import DocumentMeta, DocumentSummary

VAULT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = VAULT_ROOT / "templates"
REGISTRY_JSON = VAULT_ROOT / "registry.json"


def _load_meta(doc_dir: Path) -> Optional[DocumentMeta]:
    th_file = doc_dir / "th.md"
    if not th_file.exists():
        return None
    try:
        post = frontmatter.load(str(th_file))
        return DocumentMeta.model_validate(dict(post.metadata))
    except Exception as exc:
        print(f"[loader] Failed to parse {th_file}: {exc}")
        return None


def load_all_documents() -> list[tuple[DocumentMeta, Path]]:
    results = []
    if not TEMPLATES_DIR.exists():
        return results
    for doc_dir in sorted(TEMPLATES_DIR.iterdir()):
        if not doc_dir.is_dir():
            continue
        meta = _load_meta(doc_dir)
        if meta is not None:
            results.append((meta, doc_dir))
    return results


def get_document_content(doc_dir: Path) -> str:
    th_file = doc_dir / "th.md"
    post = frontmatter.load(str(th_file))
    return post.content


def get_usage_guide(doc_dir: Path) -> Optional[str]:
    usage_file = doc_dir / "USAGE.md"
    if usage_file.exists():
        return usage_file.read_text(encoding="utf-8")
    return None


def get_us_reference(doc_dir: Path) -> Optional[str]:
    ref_file = doc_dir / "ref-us.md"
    if ref_file.exists():
        return ref_file.read_text(encoding="utf-8")
    return None


def to_summary(meta: DocumentMeta) -> DocumentSummary:
    return DocumentSummary(
        id=meta.id,
        title=meta.title,
        title_en=meta.title_en,
        doc_type=meta.doc_type,
        status=meta.status,
        jurisdiction=meta.jurisdiction,
        requires_external_counsel=meta.requires_external_counsel,
        last_reviewed=meta.last_reviewed,
        use_cases=meta.use_cases,
    )

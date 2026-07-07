"""Pydantic models for the Legal Vault MCP server."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


DocType = Literal[
    "nda", "consulting", "privacy_policy", "customer_agreement",
    "tos", "ip_assignment", "advisor_agreement"
]
DocStatus = Literal["draft", "review", "approved", "deprecated"]
Jurisdiction = Literal["TH", "US", "TH+US"]


class ChangelogEntry(BaseModel):
    date: str
    author: str
    note: str


class DocumentMeta(BaseModel):
    id: str
    title: str
    title_en: str
    doc_type: DocType
    variant: Optional[str] = None
    jurisdiction: Jurisdiction
    governing_law: str
    language_primary: str = "th"
    frameworks: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    status: DocStatus
    approver: str
    last_reviewed: str
    next_review: Optional[str] = None
    requires_external_counsel: bool = False
    ref_us_template: Optional[str] = "ref-us.md"
    related_docs: list[str] = Field(default_factory=list)
    changelog: list[ChangelogEntry] = Field(default_factory=list)


class DocumentSummary(BaseModel):
    id: str
    title: str
    title_en: str
    doc_type: DocType
    status: DocStatus
    jurisdiction: Jurisdiction
    requires_external_counsel: bool
    last_reviewed: str
    use_cases: list[str]


class DocumentFull(BaseModel):
    id: str
    metadata: DocumentMeta
    content_th: str
    usage_guide: Optional[str] = None
    content_us_ref: Optional[str] = None
    counsel_warning: Optional[str] = None


COUNSEL_WARNING = (
    "⚠️  เอกสารนี้ต้องผ่านการตรวจสอบจากที่ปรึกษากฎหมายภายนอกก่อนใช้งานจริง "
    "ห้ามใช้ template นี้โดยตรงโดยไม่มีการ review จาก licensed attorney "
    "ในเขตอำนาจที่เกี่ยวข้อง"
)

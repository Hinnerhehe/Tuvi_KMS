"""Schema Pydantic cho API chat/ask."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(5, ge=1, le=30)
    book_codes: list[str] | None = None
    use_dense: bool = True
    use_fts: bool = True
    request_id: str | None = None


class ChatCitation(BaseModel):
    ref: str
    knowledge_ids: list[str] = []
    book_code: str
    book_title: str | None = None
    part_number: str | None = None
    pdf_page_start: int | None = None
    pdf_page_end: int | None = None
    trust_tier: int
    verification_status: str = "unverified"
    ui_badge: str | None = None
    excerpt: str


class ChatAskResponse(BaseModel):
    answer: str
    status: str = "answered"
    citations: list[ChatCitation] = []
    retrieval: dict = {}
    request_id: str = ""
    message: str | None = None
    citation_check: dict | None = None
    is_cached: bool = False

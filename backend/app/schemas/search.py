"""Schema Pydantic cho API search."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(10, ge=1, le=50)
    book_codes: list[str] | None = None
    use_dense: bool = True
    use_fts: bool = True


class Citation(BaseModel):
    index: int
    chunk_id: str
    book_code: str
    chapter: str | None = None
    part_number: str | None = None
    pdf_page_start: int | None = None
    pdf_page_end: int | None = None
    trust_tier: int
    ui_badge: str | None = None
    page_label: str | None = None
    excerpt: str
    knowledge_ids: list[str] = []


class SearchResponse(BaseModel):
    query: str
    status: str = "ok"
    results: list[dict] = []
    citations: list[Citation] = []
    meta: dict = {}

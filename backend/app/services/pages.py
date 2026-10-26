"""Parse cột PDF_Pages theo quy tắc trong column_mapping.yaml.

BD dùng "P<phần>:<trang>" (trang theo từng phần), NPL/DAU dùng "<trang>".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .mapping import Mapping


@dataclass(frozen=True)
class PageRef:
    part_number: str | None
    pdf_page: int | None

    @property
    def is_valid(self) -> bool:
        return self.pdf_page is not None


def parse_page_refs(raw: str | None, book_code: str, mapping: Mapping) -> list[PageRef]:
    """Parse chuỗi nhiều trang, ví dụ "P1:57; P1:58" hoặc "36"."""
    if not raw:
        return []
    spec = mapping.page_parsing
    separator = spec.get("separator", ";")
    patterns = spec.get("patterns", {})
    pattern = patterns.get(book_code) or patterns.get("default")
    if not pattern:
        return []
    regex = re.compile(pattern)

    refs: list[PageRef] = []
    for token in str(raw).split(separator):
        token = token.strip()
        if not token:
            continue
        m = regex.match(token)
        if not m:
            continue
        groups = m.groupdict()
        page = groups.get("page")
        try:
            page_num = int(page) if page is not None else None
        except (TypeError, ValueError):
            page_num = None
        refs.append(PageRef(part_number=groups.get("part"), pdf_page=page_num))
    return refs


def format_page_label(book_code: str, part_number: str | None, pdf_page: int | None) -> str:
    """Hiển thị theo quy ước: 'Phần N, PDF tr. X' cho BD, 'PDF tr. X' cho NPL/DAU."""
    if pdf_page is None:
        return "trang không xác định"
    if book_code == "BD" and part_number:
        return f"Phần {part_number}, PDF tr. {pdf_page}"
    return f"PDF tr. {pdf_page}"

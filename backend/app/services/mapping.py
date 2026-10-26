"""Đọc column_mapping.yaml — nguồn sự thật duy nhất cho mapping/tier/chunking."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Section:
    name: str
    sheet: str
    columns: dict[str, str]
    required: tuple[str, ...] = ()


@dataclass
class Mapping:
    raw: dict[str, Any]
    workbook_file: str
    expected_counts: dict[str, int]
    sheets_ignored: list[str]
    sections: dict[str, Section] = field(default_factory=dict)
    page_parsing: dict[str, Any] = field(default_factory=dict)
    trust_tiers: dict[str, Any] = field(default_factory=dict)
    chunking: dict[str, Any] = field(default_factory=dict)

    # --- accessors ---
    @property
    def enabled_tiers(self) -> set[int]:
        return set(self.trust_tiers.get("enabled_tiers", []))

    @property
    def default_tier(self) -> int:
        return int(self.trust_tiers.get("default_tier", 9))

    def tier_badge(self, tier: int) -> str | None:
        defs = self.trust_tiers.get("definitions", {})
        return (defs.get(tier) or {}).get("ui_badge")

    def tier_label(self, tier: int) -> str:
        defs = self.trust_tiers.get("definitions", {})
        return (defs.get(tier) or {}).get("label", f"Tier {tier}")

    def chunking_for(self, book_code: str) -> dict[str, Any]:
        strategies = self.chunking.get("strategies", {})
        return strategies.get(book_code, strategies.get("default", {}))


@lru_cache(maxsize=8)
def load_mapping(path: str | Path) -> Mapping:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    sections: dict[str, Section] = {}
    # các mục cấp top: sources, source_parts, knowledge_items, evidence,
    # id_redirects, vocabulary, taxonomy, extraction_review
    for name in (
        "sources",
        "source_parts",
        "knowledge_items",
        "evidence",
        "id_redirects",
        "vocabulary",
        "taxonomy",
        "extraction_review",
    ):
        spec = raw.get(name)
        if not spec:
            continue
        sections[name] = Section(
            name=name,
            sheet=spec["sheet"],
            columns=dict(spec.get("columns", {})),
            required=tuple(spec.get("required", ())),
        )

    return Mapping(
        raw=raw,
        workbook_file=(raw.get("workbook") or {}).get("file_name", ""),
        expected_counts=dict(raw.get("expected_counts") or {}),
        sheets_ignored=list(raw.get("sheets_ignored") or []),
        sections=sections,
        page_parsing=dict(raw.get("page_parsing") or {}),
        trust_tiers=dict(raw.get("trust_tiers") or {}),
        chunking=dict(raw.get("chunking") or {}),
    )

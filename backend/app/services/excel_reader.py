"""Đọc sheet Excel theo mapping, trả về DataFrame đã đổi tên cột sang tên field."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .mapping import Mapping, Section


def read_sheet(excel: Path, section: Section) -> pd.DataFrame:
    """Đọc 1 sheet và đổi tên cột theo mapping (Excel tên -> tên field)."""
    df = pd.read_excel(excel, sheet_name=section.sheet)
    df = df.rename(columns={excel_col: field for field, excel_col in section.columns.items()})
    keep = [c for c in section.columns if c in df.columns]
    return df[keep].copy()


def read_section(excel: Path, mapping: Mapping, name: str) -> pd.DataFrame:
    if name not in mapping.sections:
        raise KeyError(f"section không có trong mapping: {name}")
    return read_sheet(excel, mapping.sections[name])


def find_excel(explicit: Path | None, mapping: Mapping) -> Path:
    """Tìm file Excel: ưu tiên đường dẫn chỉ định, sau đó tới data/raw/."""
    if explicit and explicit.exists():
        return explicit
    candidates = [
        Path("data/raw") / mapping.workbook_file,
        Path(mapping.workbook_file),
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"Không tìm thấy {mapping.workbook_file}. "
        f"Đặt file vào data/raw/ hoặc truyền --excel."
    )

"""Chuẩn hóa văn bản tiếng Việt: NFC, bỏ dấu, hash nội dung."""
from __future__ import annotations

import hashlib
import re
import unicodedata

_WS = re.compile(r"\s+")
# chữ 'đ' không tách được bằng NFD
_D_MAPPING = {"đ": "d", "Đ": "D"}


def nfc(text: str | None) -> str:
    """Unicode NFC + gọn khoảng trắng, giữ nguyên nội dung."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    return _WS.sub(" ", text).strip()


def strip_accents(text: str | None) -> str:
    """Bỏ dấu, đưa về chữ thường — dùng cho FTS5 để tìm 'tu vi' == 'Tử Vi'."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    text = "".join(_D_MAPPING.get(ch, ch) for ch in text)
    text = "".join(
        ch for ch in unicodedata.normalize("NFD", text) if not unicodedata.combining(ch)
    )
    return text.lower()


def content_hash(text: str | None) -> str:
    """Hash nội dung đã chuẩn hóa — dùng phát hiện trùng và upsert."""
    normalized = strip_accents(nfc(text))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

"""T11 — Kiểm tra citation tự động.

Kiểm 3 điều (plan §5.8):
  1. Mọi số [n] trong câu trả lời phải tồn tại trong ngữ cảnh đã đưa cho LLM.
  2. Phát hiện câu có nội dung nhưng không kèm citation.
  3. Trích dẫn phải thuộc đúng sách/phần/trang đã khai báo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

CITATION_RE = re.compile(r"\[(\d+)\]")


@dataclass
class CitationCheck:
    valid: bool
    cited_refs: list[int] = field(default_factory=list)
    invalid_refs: list[int] = field(default_factory=list)
    unused_refs: list[int] = field(default_factory=list)
    uncited_claims: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "cited_refs": self.cited_refs,
            "invalid_refs": self.invalid_refs,
            "unused_refs": self.unused_refs,
            "uncited_claims": self.uncited_claims,
            "message": self.message,
        }


def extract_refs(text: str | None) -> list[int]:
    """Lấy danh sách số tham chiếu [n] trong văn bản, giữ thứ tự, bỏ trùng."""
    if not text:
        return []
    seen: set[int] = set()
    refs: list[int] = []
    for m in CITATION_RE.finditer(text):
        n = int(m.group(1))
        if n not in seen:
            seen.add(n)
            refs.append(n)
    return refs


def split_sentences(text: str | None) -> list[str]:
    """Tách câu theo dấu kết tiếng Việt + tiếng Anh."""
    if not text:
        return []
    parts = re.split(r"(?<=[.!?…])\s+|\n+", text)
    return [p.strip() for p in parts if p and p.strip()]


def _is_claim(sentence: str) -> bool:
    """Câu có nội dung khẳng định cần trích dẫn (bỏ qua câu chào/liệt kê nhãn)."""
    s = sentence.strip()
    if len(s) < 15:
        return False
    # câu chỉ chứa nhãn sách / tiêu đề / gạch đầu dòng
    if re.fullmatch(r"[\s\-\*•\d\.\[\]]+", s):
        return False
    if re.match(r"^(theo|According to)\s", s, flags=re.IGNORECASE) is None and s.endswith(":"):
        return False
    return True


def validate_citations(
    answer: str | None,
    allowed_refs: list[int] | set[int],
    require_citations: bool = True,
) -> CitationCheck:
    """Kiểm citation của câu trả lời so với tập ref hợp lệ.

    `allowed_refs` = danh sách số tham chiếu đã đưa vào ngữ cảnh.
    """
    allowed = set(allowed_refs)
    cited = extract_refs(answer)
    invalid = [r for r in cited if r not in allowed]
    unused = sorted(allowed - set(cited))

    uncited: list[str] = []
    if require_citations:
        for sentence in split_sentences(answer):
            if not _is_claim(sentence):
                continue
            if not CITATION_RE.search(sentence):
                uncited.append(sentence)

    valid = not invalid and (not require_citations or not uncited)
    if invalid:
        message = f"Trích dẫn không có trong ngữ cảnh: {invalid}"
    elif uncited:
        message = f"{len(uncited)} câu không kèm trích dẫn"
    else:
        message = "OK"

    return CitationCheck(
        valid=valid,
        cited_refs=cited,
        invalid_refs=invalid,
        unused_refs=unused,
        uncited_claims=uncited,
        message=message,
    )


def strip_invalid_citations(answer: str | None, allowed_refs: list[int] | set[int]) -> str:
    """Xoá các tham chiếu [n] không có trong ngữ cảnh (sanitize trước khi trả về)."""
    if not answer:
        return ""
    allowed = set(allowed_refs)

    def repl(m: re.Match) -> str:
        return m.group(0) if int(m.group(1)) in allowed else ""

    return CITATION_RE.sub(repl, answer)

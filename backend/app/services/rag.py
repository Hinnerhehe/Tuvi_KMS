"""T12 — Orchestrator RAG: retrieval -> kiểm ngưỡng -> prompt -> LLM -> citation.

Status trả về (plan §5.1):
  answered | insufficient_evidence | out_of_scope | error
"""
from __future__ import annotations

import re
import os
import uuid
from dataclasses import dataclass, field
from typing import Any

from backend.app.core.config import EXCERPT_MAX_CHARS, RETRIEVAL_CONFIG
from backend.app.schemas.chat import ChatAskResponse, ChatCitation
from backend.app.services.cache import CacheService, get_prompt_hash
from backend.app.services.citation_validator import (
    strip_invalid_citations,
    validate_citations,
)
from backend.app.services.llm_provider import (
    ANSWER_PROMPT,
    BOOK_TITLES,
    SYSTEM_PROMPT,
    LLMError,
    get_llm_provider,
)
from backend.app.services.pages import format_page_label
from backend.app.services.retriever import RetrievedChunk, Retriever

# --- PHÁT HIỆN YÊU CẦU NGOÀI PHẠM VI (Defense-in-depth Layer 1) ---
DIRECT_DIVINATION_PATTERNS = [
    r"\b(?:xem|lập|chấm|an|làm|luận)\s+(?:lá\s*số|tướng\s*số|tử\s*vi|vận\s*hạn)\b",
    r"\b(?:coi\s*bói|xem\s*bói|bói\s*toán)\b",
]
FIRST_PERSON_PATTERNS = r"\b(tôi|em|mình|con|cháu)\b"
PERSONAL_TOPICS = (
    r"(?:đổi\s+việc|chuyển\s+việc|nghỉ\s+việc|nhảy\s+việc|"
    r"lấy\s+chồng|lấy\s+vợ|kết\s+hôn|cưới|ly\s+hôn|sinh\s+con|"
    r"mua\s+nhà|đầu\s+tư|kinh\s+doanh|xuất\s+ngoại|đi\s+xa|"
    r"phát\s+tài|trúng\s+số|giàu\s+không|hạn|ốm\s+đau|tai\s+nạn)"
)
TIME_MARKERS = r"\b(năm\s+nay|năm\s+sau|năm\s+tới|tháng\s+này|tháng\s+sau|tuổi\s+này|sắp\s+tới)\b"
BIRTH_INFO_PATTERNS = r"(?:sinh\s+năm\s+\d{4}|sinh\s+ngày\s+\d{1,2}|sinh\s+vào\s+ngày|sinh\s+giờ\s+\w+)"


def detect_out_of_scope(question: str) -> tuple[bool, str | None]:
    """Phát hiện câu hỏi ngoài phạm vi MVP. Trả (is_out_of_scope, lý do).
    
    Áp dụng nguyên tắc phòng vệ phân tầng:
    Chỉ chặn khi câu hỏi thể hiện rõ ý định bói toán/hỏi vận mệnh cho cá nhân.
    Không chặn nhầm các câu hỏi tra cứu lý thuyết học thuật có chứa từ khóa liên quan.
    """
    q = question.lower()

    # 1. Trực tiếp yêu cầu an/xem/chấm/luận lá số hoặc bói toán
    for p in DIRECT_DIVINATION_PATTERNS:
        if re.search(p, q):
            return True, "Yêu cầu an/luận lá số hoặc bói toán cá nhân nằm ngoài phạm vi MVP."

    # 2. Cung cấp thông tin ngày giờ sinh kèm đại từ hoặc nhờ vả
    if re.search(BIRTH_INFO_PATTERNS, q) and (
        re.search(FIRST_PERSON_PATTERNS, q) or re.search(r"\b(cho|hộ|giúp)\b", q)
    ):
        return True, "Cung cấp thông tin cá nhân để dự báo nằm ngoài phạm vi tra cứu tài liệu."

    # 3. Kết hợp đại từ ngôi thứ nhất + chủ đề quyết định cuộc đời / thời vận
    if re.search(FIRST_PERSON_PATTERNS, q):
        # "vận mệnh của tôi/em...", "số phận của mình..."
        if re.search(
            r"(?:vận\s*mệnh|tương\s*lai|số\s*phận|cuộc\s*đời|hậu\s*vận|lá\s*số)\s+của\s+"
            + FIRST_PERSON_PATTERNS,
            q,
        ) or re.search(r"\bcủa\s+" + FIRST_PERSON_PATTERNS, q):
            return True, "Hỏi về số phận, vận mệnh cá nhân nằm ngoài phạm vi MVP."

        # Đại từ + chủ đề cá nhân
        if re.search(PERSONAL_TOPICS, q):
            return True, "Hỏi lời khuyên hoặc dự báo tương lai cho cá nhân nằm ngoài phạm vi tra cứu học thuật."

        # Đại từ + mốc thời gian + hỏi kết quả
        if re.search(TIME_MARKERS, q) and re.search(
            r"(?:thế\s+nào|ra\s+sao|ổn\s+không|tốt\s+không|sao\s+không|được\s+không)", q
        ):
            return True, "Hỏi dự báo thời vận cá nhân nằm ngoài phạm vi MVP."

    return False, None


@dataclass
class BuildContext:
    """Kết quả bước chuẩn bị ngữ cảnh cho LLM."""

    chunks: list[RetrievedChunk]
    allowed_refs: list[int] = field(default_factory=list)
    books_covered: list[str] = field(default_factory=list)
    num_candidates: int = 0

    @property
    def has_evidence(self) -> bool:
        return bool(self.chunks)


class RAGPipeline:
    def __init__(
        self,
        retriever: Retriever | None = None,
        provider_name: str | None = None,
        max_context: int | None = None,
        rrf_threshold: float | None = None,
    ):
        self.retriever = retriever or Retriever()
        self.provider_name = provider_name
        self.cache = CacheService()
        cfg = self._load_retrieval_cfg()
        self.max_context = max_context or int(cfg.get("max_context_chunks", 8))
        self.rrf_threshold = (
            rrf_threshold
            if rrf_threshold is not None
            else float(cfg.get("abstain_rrf_threshold", 0.005))
        )

    @staticmethod
    def _load_retrieval_cfg() -> dict:
        import yaml

        path = RETRIEVAL_CONFIG
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    # --- bước 1: chuẩn bị ngữ cảnh ---
    def build_context(
        self, question: str, top_k: int = 5, book_codes: list[str] | None = None
    ) -> BuildContext:
        candidates = self.retriever.search(
            question,
            top_k=self.max_context * 3,
            book_codes=book_codes,
        )
        # lọc theo ngưỡng RRF
        kept = [c for c in candidates if c.rrf_score >= self.rrf_threshold]
        # giới hạn số ngữ cảnh, nhưng bảo đảm mỗi sách có đại diện
        selected = self._select_with_book_coverage(kept, self.max_context)
        return BuildContext(
            chunks=selected,
            allowed_refs=list(range(1, len(selected) + 1)),
            books_covered=sorted({c.book_code for c in selected}),
            num_candidates=len(candidates),
        )

    @staticmethod
    def _select_with_book_coverage(
        chunks: list[RetrievedChunk], limit: int
    ) -> list[RetrievedChunk]:
        """Chọn tối đa `limit` chunk, ưu tiên mỗi sách có ít nhất một đại diện."""
        if len(chunks) <= limit:
            return chunks
        selected: list[RetrievedChunk] = []
        seen_books: set[str] = set()
        # vòng 1: mỗi sách một đại diện (đi theo thứ tự điểm)
        for c in chunks:
            if c.book_code not in seen_books:
                selected.append(c)
                seen_books.add(c.book_code)
                if len(selected) >= limit:
                    return selected
        # vòng 2: lấp đầy từ các chunk còn lại theo điểm
        for c in chunks:
            if len(selected) >= limit:
                break
            if c not in selected:
                selected.append(c)
        selected.sort(key=lambda c: -c.rrf_score)
        return selected

    # --- bước 2: dựng prompt ---
    @staticmethod
    def build_prompt(question: str, ctx: BuildContext) -> tuple[str, str]:
        parts: list[str] = []
        for i, c in enumerate(ctx.chunks, start=1):
            label = format_page_label(c.book_code, c.part_number, c.pdf_page_start)
            parts.append(
                f"[{i}] (Sách: {c.book_code} | Chương: {c.chapter or '-'} | "
                f"{label} | Mức tin cậy: tier {c.trust_tier})\n{c.text}"
            )
        context = "\n\n".join(parts)
        return SYSTEM_PROMPT, ANSWER_PROMPT.format(
            context=context, question=question
        )

    # --- bước 3: trả lời ---
    def ask(
        self,
        question: str,
        top_k: int = 5,
        book_codes: list[str] | None = None,
        request_id: str | None = None,
    ) -> ChatAskResponse:
        request_id = request_id or str(uuid.uuid4())
        question = (question or "").strip()

        if not question:
            return ChatAskResponse(
                answer="",
                status="error",
                citations=[],
                retrieval={"num_candidates": 0, "num_contexts": 0, "books_covered": []},
                request_id=request_id,
                message="Câu hỏi rỗng.",
            )

        model_name = self.provider_name or os.getenv("KMS_LLM_PROVIDER", "gemini")
        prompt_hash = get_prompt_hash(SYSTEM_PROMPT, ANSWER_PROMPT)

        # 1. Tra cứu Cache tất định (Deterministic Query Cache)
        cached = self.cache.lookup(
            question=question,
            book_codes=book_codes,
            model_name=model_name,
            prompt_hash=prompt_hash,
        )
        if cached is not None:
            cached.request_id = request_id
            return cached

        # 2. Phát hiện yêu cầu ngoài phạm vi (Defense Layer 1)
        is_oos, reason = detect_out_of_scope(question)
        if is_oos:
            res = ChatAskResponse(
                answer=(
                    "Nội dung này nằm ngoài phạm vi của hệ thống. "
                    "Hệ thống chỉ tra cứu và trích dẫn nội dung trong ba cuốn sách "
                    "Tử Vi nêu trên; không luận giải lá số hay dự báo cho cá nhân."
                ),
                status="out_of_scope",
                citations=[],
                retrieval={"num_candidates": 0, "num_contexts": 0, "books_covered": []},
                request_id=request_id,
                message=reason,
            )
            self.cache.save(question, book_codes, model_name, prompt_hash, res)
            return res

        try:
            ctx = self.build_context(question, top_k=top_k, book_codes=book_codes)
        except Exception as exc:
            return ChatAskResponse(
                answer="",
                status="error",
                citations=[],
                retrieval={"num_candidates": 0, "num_contexts": 0, "books_covered": []},
                request_id=request_id,
                message=f"Lỗi truy xuất: {exc}",
            )

        if not ctx.has_evidence:
            res = ChatAskResponse(
                answer=(
                    "Tài liệu không đủ căn cứ để trả lời câu này. "
                    "Hãy thử dùng thuật ngữ khác hoặc hỏi về nội dung trong ba sách nguồn."
                ),
                status="insufficient_evidence",
                citations=[],
                retrieval={
                    "num_candidates": ctx.num_candidates,
                    "num_contexts": 0,
                    "books_covered": [],
                },
                request_id=request_id,
                message="Không tìm thấy ngữ cảnh vượt ngưỡng.",
            )
            self.cache.save(question, book_codes, model_name, prompt_hash, res)
            return res

        system_prompt, user_prompt = self.build_prompt(question, ctx)

        try:
            provider = get_llm_provider(self.provider_name)
            resp = provider.generate(system_prompt, user_prompt)
            answer = resp.text
        except LLMError as exc:
            return ChatAskResponse(
                answer="",
                status="error",
                citations=[],
                retrieval={
                    "num_candidates": ctx.num_candidates,
                    "num_contexts": len(ctx.chunks),
                    "books_covered": ctx.books_covered,
                },
                request_id=request_id,
                message=f"Lỗi LLM: {exc}",
            )
        except Exception as exc:
            return ChatAskResponse(
                answer="",
                status="error",
                citations=[],
                retrieval={
                    "num_candidates": ctx.num_candidates,
                    "num_contexts": len(ctx.chunks),
                    "books_covered": ctx.books_covered,
                },
                request_id=request_id,
                message=f"Lỗi không mong đợi: {exc}",
            )

        # kiểm citation
        check = validate_citations(answer, ctx.allowed_refs)
        answer = strip_invalid_citations(answer, ctx.allowed_refs)

        citations = [
            ChatCitation(
                ref=str(i),
                knowledge_ids=c.knowledge_ids,
                book_code=c.book_code,
                book_title=BOOK_TITLES.get(c.book_code, c.book_code),
                part_number=c.part_number,
                pdf_page_start=c.pdf_page_start,
                pdf_page_end=c.pdf_page_end,
                trust_tier=c.trust_tier,
                verification_status="unverified",
                ui_badge=_tier_badge(c.trust_tier),
                excerpt=(c.text or "")[:EXCERPT_MAX_CHARS],
            )
            for i, c in enumerate(ctx.chunks, start=1)
        ]

        res = ChatAskResponse(
            answer=answer,
            status="answered",
            citations=citations,
            retrieval={
                "num_candidates": ctx.num_candidates,
                "num_contexts": len(ctx.chunks),
                "books_covered": ctx.books_covered,
            },
            request_id=request_id,
            citation_check=check.to_dict(),
            message=check.message,
        )
        self.cache.save(question, book_codes, model_name, prompt_hash, res)
        return res


def _tier_badge(tier: int) -> str:
    from backend.app.services.mapping import load_mapping
    from backend.app.core.config import MAPPING_PATH

    mapping = load_mapping(MAPPING_PATH)
    return mapping.tier_badge(tier) or mapping.tier_label(tier)

"""Dịch vụ Query Cache có kiểm soát phiên bản (Versioned Deterministic Cache).

Đảm bảo:
  1. Cùng một câu hỏi và cùng bối cảnh -> trả về đúng 100% câu trả lời đã lưu.
  2. Khóa cache phức hợp (Composite Key) phụ thuộc:
       - Câu hỏi chuẩn hóa (normalized_question)
       - Bộ lọc sách (book_codes)
       - Tên mô hình LLM (model_name)
       - Hash của System Prompt & Answer Prompt (prompt_hash)
       - Hash phiên bản dữ liệu/index thật từ index_manifest.json (index_version)
  3. KHÔNG lưu cache khi có lỗi (status == 'error' hoặc exception).
  4. Hỗ trợ vô hiệu hóa/xóa cache khi cần (clear_cache).
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select, update

from backend.app.core.config import (
    DB_PATH,
    ENABLE_QUERY_CACHE,
    GEMINI_MODEL,
    LLM_PROVIDER,
    MANIFEST_PATH,
)
from backend.app.db.models import QueryCache
from backend.app.db.session import init_db, session_scope
from backend.app.schemas.chat import ChatAskResponse

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_question(q: str) -> str:
    """Chuẩn hóa câu hỏi: chữ thường, cắt khoảng trắng đầu/cuối và khoảng trắng thừa.
    Giữ nguyên toàn bộ dấu tiếng Việt để không làm biến đổi ngữ nghĩa."""
    return " ".join(q.strip().lower().split())


def get_index_version() -> str:
    """Đọc hash phiên bản index thật từ file index_manifest.json.
    Nếu file thay đổi (reindex dữ liệu), giá trị hash sẽ tự động thay đổi,
    khiến toàn bộ cache cũ bị vô hiệu hóa an toàn."""
    if MANIFEST_PATH.exists():
        try:
            content = MANIFEST_PATH.read_bytes()
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception as exc:
            logger.warning("Không đọc được index_manifest.json: %s", exc)

    if DB_PATH.exists():
        try:
            stat = DB_PATH.stat()
            return hashlib.sha256(f"{stat.st_size}_{stat.st_mtime}".encode()).hexdigest()[:16]
        except Exception:
            pass

    return "v0.1_base"


def get_prompt_hash(system_prompt: str, answer_prompt_template: str) -> str:
    """Hash nội dung prompt. Bất kỳ sự thay đổi nào về prompt chỉ thị
    sẽ làm thay đổi hash, vô hiệu hóa cache cũ."""
    blob = f"{system_prompt.strip()}\n---\n{answer_prompt_template.strip()}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def compute_cache_key(
    normalized_question: str,
    book_codes: list[str] | None,
    model_name: str,
    prompt_hash: str,
    index_version: str,
) -> str:
    """Tính SHA-256 composite key."""
    books_key = ",".join(sorted(book_codes)) if book_codes else "ALL"
    raw_key = f"{normalized_question}||{books_key}||{model_name}||{prompt_hash}||{index_version}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class CacheService:
    def __init__(self) -> None:
        init_db()

    def lookup(
        self,
        question: str,
        book_codes: list[str] | None,
        model_name: str,
        prompt_hash: str,
    ) -> ChatAskResponse | None:
        """Tra cứu cache. Trả về ChatAskResponse (kèm is_cached=True) nếu trúng cache."""
        if not ENABLE_QUERY_CACHE:
            return None

        norm_q = normalize_question(question)
        idx_ver = get_index_version()
        key = compute_cache_key(norm_q, book_codes, model_name, prompt_hash, idx_ver)

        try:
            with session_scope() as session:
                entry = session.execute(
                    select(QueryCache).where(QueryCache.cache_key == key)
                ).scalar_one_or_none()

                if entry is None:
                    return None

                # Cập nhật số lần trúng và thời gian
                session.execute(
                    update(QueryCache)
                    .where(QueryCache.cache_key == key)
                    .values(hit_count=entry.hit_count + 1, last_hit_at=utcnow())
                )

                data = json.loads(entry.response_json)
                resp = ChatAskResponse(**data)
                resp.is_cached = True
                return resp
        except Exception as exc:
            logger.warning("Lỗi tra cứu query_cache: %s", exc)
            return None

    def save(
        self,
        question: str,
        book_codes: list[str] | None,
        model_name: str,
        prompt_hash: str,
        response: ChatAskResponse,
    ) -> bool:
        """Lưu câu trả lời vào cache.
        QUY TẮC BẢO VỆ: Chỉ lưu khi trạng thái thành công ('answered', 'out_of_scope', 'insufficient_evidence').
        Tuyệt đối không lưu khi trạng thái là 'error' hoặc lỗi timeout!"""
        if not ENABLE_QUERY_CACHE:
            return False

        if response.status not in ("answered", "out_of_scope", "insufficient_evidence"):
            return False

        norm_q = normalize_question(question)
        idx_ver = get_index_version()
        key = compute_cache_key(norm_q, book_codes, model_name, prompt_hash, idx_ver)
        books_key = ",".join(sorted(book_codes)) if book_codes else "ALL"

        try:
            # Lưu dữ liệu sạch, mặc định cờ is_cached=False trong payload gốc
            payload = response.model_dump()
            payload["is_cached"] = False
            response_json = json.dumps(payload, ensure_ascii=False)

            with session_scope() as session:
                existing = session.execute(
                    select(QueryCache).where(QueryCache.cache_key == key)
                ).scalar_one_or_none()

                if existing is not None:
                    existing.response_json = response_json
                    existing.last_hit_at = utcnow()
                else:
                    new_entry = QueryCache(
                        cache_key=key,
                        question=question,
                        normalized_question=norm_q,
                        book_codes=books_key,
                        model_name=model_name,
                        prompt_hash=prompt_hash,
                        index_version=idx_ver,
                        status=response.status,
                        response_json=response_json,
                        hit_count=1,
                        created_at=utcnow(),
                        last_hit_at=utcnow(),
                    )
                    session.add(new_entry)
            return True
        except Exception as exc:
            logger.warning("Lỗi lưu query_cache: %s", exc)
            return False

    def clear(self) -> int:
        """Xóa toàn bộ cache khi cần làm sạch dữ liệu."""
        try:
            with session_scope() as session:
                result = session.execute(delete(QueryCache))
                return result.rowcount
        except Exception as exc:
            logger.error("Lỗi khi xóa cache: %s", exc)
            return 0

    def stats(self) -> dict[str, Any]:
        """Thống kê trạng thái cache."""
        try:
            with session_scope() as session:
                total_entries = session.execute(select(func.count(QueryCache.cache_key))).scalar() or 0
                total_hits = session.execute(select(func.sum(QueryCache.hit_count))).scalar() or 0
                return {
                    "enabled": ENABLE_QUERY_CACHE,
                    "index_version": get_index_version(),
                    "total_cached_queries": total_entries,
                    "total_hits": total_hits,
                }
        except Exception as exc:
            return {"enabled": ENABLE_QUERY_CACHE, "error": str(exc)}

"""Bộ kiểm thử cho hệ thống Query Cache có kiểm soát phiên bản."""
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.schemas.chat import ChatAskResponse, ChatCitation
from backend.app.services.cache import (
    CacheService,
    compute_cache_key,
    get_index_version,
    get_prompt_hash,
    normalize_question,
)


def test_cache_roundtrip():
    service = CacheService()
    service.clear()

    q = "Sao Thiên Phủ ở cung Mệnh có ý nghĩa gì?"
    book_codes = ["NPL", "DAU"]
    model_name = "test-model"
    prompt_hash = "hash123"

    # Lần 1: Chưa có trong cache
    assert service.lookup(q, book_codes, model_name, prompt_hash) is None

    # Tạo response giả lập
    mock_resp = ChatAskResponse(
        answer="Sao Thiên Phủ là lệnh tinh, chủ về tài lộc và quyền uy.",
        status="answered",
        citations=[
            ChatCitation(
                ref="1",
                book_code="NPL",
                pdf_page_start=45,
                trust_tier=1,
                excerpt="Thiên Phủ miếu địa",
            )
        ],
        retrieval={"num_contexts": 1},
    )

    # Lưu vào cache
    saved = service.save(q, book_codes, model_name, prompt_hash, mock_resp)
    assert saved is True

    # Lần 2: Phải trúng cache và có cờ is_cached=True
    hit_resp = service.lookup(q, book_codes, model_name, prompt_hash)
    assert hit_resp is not None
    assert hit_resp.is_cached is True
    assert hit_resp.answer == mock_resp.answer
    assert len(hit_resp.citations) == 1
    assert hit_resp.citations[0].pdf_page_start == 45

    # Lần 3: Câu hỏi viết hoa/thêm khoảng trắng thừa -> VẪN PHẢI TRÚNG CACHE
    q_messy = "   sao   thiên phủ ở cung Mệnh có ý nghĩa gì?   "
    hit_messy = service.lookup(q_messy, book_codes, model_name, prompt_hash)
    assert hit_messy is not None
    assert hit_messy.is_cached is True


def test_do_not_cache_errors():
    service = CacheService()
    service.clear()

    q = "Câu hỏi bị lỗi timeout"
    model_name = "test-model"
    prompt_hash = "hash123"

    error_resp = ChatAskResponse(
        answer="",
        status="error",
        message="LLM Timeout",
    )

    # Không được phép lưu lỗi
    saved = service.save(q, None, model_name, prompt_hash, error_resp)
    assert saved is False

    # Tra cứu lại phải là None
    assert service.lookup(q, None, model_name, prompt_hash) is None


def test_cache_invalidates_on_prompt_or_version_change():
    service = CacheService()
    service.clear()

    q = "Sao Thái Dương"
    model_name = "test-model"
    prompt_hash_v1 = "prompt_v1"
    prompt_hash_v2 = "prompt_v2"

    resp = ChatAskResponse(
        answer="Thái Dương là vầng nhật quang.",
        status="answered",
    )

    service.save(q, None, model_name, prompt_hash_v1, resp)

    # Đúng version prompt -> trúng cache
    assert service.lookup(q, None, model_name, prompt_hash_v1) is not None

    # Thay đổi prompt -> cache miss an toàn, không trả kết quả cũ
    assert service.lookup(q, None, model_name, prompt_hash_v2) is None


def test_cache_clear_and_stats():
    service = CacheService()
    service.clear()

    resp = ChatAskResponse(answer="A", status="answered")
    service.save("câu 1", None, "m", "h", resp)
    service.save("câu 2", None, "m", "h", resp)

    stats = service.stats()
    assert stats["total_cached_queries"] == 2

    cleared = service.clear()
    assert cleared == 2
    assert service.stats()["total_cached_queries"] == 0


if __name__ == "__main__":
    print("=" * 60)
    print("CHẠY KIỂM THỬ QUERY CACHE (DETERMINISTIC CACHE TEST)")
    print("=" * 60)
    test_cache_roundtrip()
    print("[PASS] test_cache_roundtrip")
    test_do_not_cache_errors()
    print("[PASS] test_do_not_cache_errors")
    test_cache_invalidates_on_prompt_or_version_change()
    print("[PASS] test_cache_invalidates_on_prompt_or_version_change")
    test_cache_clear_and_stats()
    print("[PASS] test_cache_clear_and_stats")
    print("\nTẤT CẢ TEST ĐỀU THÀNH CÔNG!")

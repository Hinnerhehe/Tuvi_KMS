"""P2: prompt chỉ-dữ-kiện, fallback truy xuất và kiểm tra độ cụ thể."""
from __future__ import annotations

from unittest.mock import patch

from backend.app.services import horoscope_interpreter as interpreter
from backend.app.services.horoscope_analysis import build_star_facts
from backend.app.services.horoscope_interpreter import (
    build_horoscope_user_prompt, check_specificity, interpret_horoscope,
)
from backend.app.services.horoscope_rag_bridge import (
    format_context_for_prompt, generate_horoscope_queries, retrieve_horoscope_context,
)
from tests.horoscope_support import gemini_response, make_features, valid_reading

GOLDEN_LAYMAN = (
    "Bạn là người mềm dẻo, linh hoạt",
    "Đại diện cho mẫu người hành động, dám nghĩ dám làm",
    "Bạn được hoàn cảnh và môi trường ưu ái nâng đỡ",
)


def test_prompt_has_data_but_no_static_layman_text():
    features = make_features(2026)
    context = retrieve_horoscope_context(features, 2)
    prompt = build_horoscope_user_prompt(features, format_context_for_prompt(context))
    for golden in GOLDEN_LAYMAN:
        assert golden not in prompt
    assert "Ất Hợi" in prompt
    assert "Bính Ngọ" in prompt and "2026" in prompt
    assert "luu_nien" in prompt


def test_retrieval_relaxes_palace_suffix_when_no_hit():
    features = make_features(2026)
    queries = generate_horoscope_queries(features)
    baseline_calls = sum(len(v) for v in queries.values())
    calls: list[str] = []

    def fake_search(query, limit=5, book_code=None, db_path=None):
        calls.append(query)
        if " cung " in query:
            return []
        return [{
            "chunk_id": "c1", "book_code": "NPL", "chapter": "Thử",
            "text": "Thiên Cơ lưu hạn cần đối chiếu.", "excerpt": "Thiên Cơ lưu hạn cần đối chiếu.",
            "score": -1.0, "part_number": None, "pdf_page_start": 1, "pdf_page_end": 1,
            "trust_tier": 1, "matched_stars": ["thien co"], "matched_query": query,
        }]

    with patch("backend.app.services.horoscope_rag_bridge.search_fts_sqlite", side_effect=fake_search):
        context = retrieve_horoscope_context(features, 2)

    relaxed_calls = [q for q in calls if " cung " not in q]
    assert relaxed_calls
    assert context["query_count"] > baseline_calls
    assert context["reference_list"]
    assert all(" cung " not in hit["matched_query"] for hit in context["reference_list"])


def test_specificity_requires_three_facts_and_the_viewed_year():
    features = make_features(2026)
    context = retrieve_horoscope_context(features, 2)
    facts = build_star_facts(features, context)

    good = valid_reading(facts, "2026 Bính Ngọ", fact_count=3)
    assert check_specificity(good, features, context) is None

    few_facts = valid_reading(facts, "2026 Bính Ngọ", fact_count=1)
    assert check_specificity(few_facts, features, context)

    no_year = valid_reading(facts, "2026 Bính Ngọ", fact_count=3, include_year=False)
    assert check_specificity(no_year, features, context)


def test_interpret_retries_once_when_specificity_is_low():
    features = make_features(2026)
    context = retrieve_horoscope_context(features, 2)
    facts = build_star_facts(features, context)
    low = valid_reading(facts, "2026 Bính Ngọ", fact_count=1)
    good = valid_reading(facts, "2026 Bính Ngọ", fact_count=3)

    with patch.object(interpreter, "GEMINI_API_KEY", "test-key"), patch(
        "backend.app.services.horoscope_interpreter.requests.post",
        side_effect=[gemini_response(low), gemini_response(good)],
    ) as post:
        reading = interpret_horoscope(features, format_context_for_prompt(context), "auto", context)

    assert post.call_count == 2
    assert reading["_generation"]["attempts"] == 2
    assert reading["_generation"]["specificity_low"] is False

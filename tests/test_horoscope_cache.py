"""P3: cache bài luận giải — trúng khi lặp lại, miss khi đổi năm, không lưu lỗi."""
from __future__ import annotations

import requests
from unittest.mock import patch

from backend.app.services import horoscope_cache
from backend.app.services import horoscope_interpreter as interpreter
from backend.app.services.horoscope_rag_bridge import format_context_for_prompt, retrieve_horoscope_context
from backend.app.services.horoscope_service import read_horoscope
from tests.horoscope_support import gemini_response, make_features, make_request, valid_reading


def _reading_for(year: int, fact_count: int = 3) -> dict:
    features = make_features(year)
    context = retrieve_horoscope_context(features, 4)
    facts = [f for f in _facts_with_refs(features, context)]
    year_text = f"{year} {features['nam_xem']['can_chi']}"
    return valid_reading(facts, year_text, fact_count=fact_count)


def _facts_with_refs(features, context):
    from backend.app.services.horoscope_analysis import build_star_facts
    return build_star_facts(features, context)


def test_same_input_and_year_hits_cache_after_one_llm_call():
    horoscope_cache.clear()
    reading = _reading_for(2026)
    request = make_request(provider="auto", target_year=2026, top_k_per_topic=4)
    with patch.object(interpreter, "GEMINI_API_KEY", "test-key"), patch(
        "backend.app.services.horoscope_interpreter.requests.post",
        return_value=gemini_response(reading),
    ) as post:
        first = read_horoscope(request)
        second = read_horoscope(request)
    assert post.call_count == 1
    assert first["meta"]["cached"] is False
    assert second["meta"]["cached"] is True
    assert second["reading"] == first["reading"]
    assert second["meta"]["actual_provider"] == "gemini"


def test_changing_the_year_misses_cache():
    horoscope_cache.clear()
    request_2026 = make_request(provider="auto", target_year=2026, top_k_per_topic=4)
    request_2027 = make_request(provider="auto", target_year=2027, top_k_per_topic=4)
    with patch.object(interpreter, "GEMINI_API_KEY", "test-key"), patch(
        "backend.app.services.horoscope_interpreter.requests.post",
        side_effect=[gemini_response(_reading_for(2026)), gemini_response(_reading_for(2027))],
    ) as post:
        first = read_horoscope(request_2026)
        second = read_horoscope(request_2027)
    assert post.call_count == 2
    assert first["meta"]["cached"] is False
    assert second["meta"]["cached"] is False
    assert first["meta"]["target_year"] == 2026
    assert second["meta"]["target_year"] == 2027


def test_timeout_is_not_cached():
    horoscope_cache.clear()
    request = make_request(provider="auto", target_year=2026, top_k_per_topic=4)
    with patch.object(interpreter, "GEMINI_API_KEY", "test-key"), patch(
        "backend.app.services.horoscope_interpreter.requests.post",
        side_effect=[requests.Timeout("quá hạn"), gemini_response(_reading_for(2026))],
    ) as post:
        first = read_horoscope(request)
        second = read_horoscope(request)
    assert first["meta"]["actual_provider"] == "mock"
    assert first["meta"]["reason"] == "timeout"
    assert post.call_count == 2
    assert second["meta"]["actual_provider"] == "gemini"
    assert second["meta"]["cached"] is False


def test_change_index_version_invalidates_key():
    birth = {"ngay": 1, "thang": 1, "nam": 1990, "chi_gio": "Tý", "gioi_tinh": "Nam"}
    key_old = horoscope_cache.compute_key(birth, "auto", "gemini-2.5-flash", "ctx", "v1")
    key_new = horoscope_cache.compute_key(birth, "auto", "gemini-2.5-flash", "ctx", "v2")
    assert key_old != key_new


def test_prompt_excerpts_are_short_but_ui_citations_stay_long():
    features = make_features(2026)
    context = retrieve_horoscope_context(features, 4)
    prompt = format_context_for_prompt(context)
    assert context["reference_list"]
    for ref in context["reference_list"]:
        marker = f"[{ref['ref_id']}] "
        start = prompt.index(marker)
        body = prompt[start + len(marker):].split("\n\n", 1)[0]
        excerpt_in_prompt = body.split("\n", 1)[1]
        assert len(excerpt_in_prompt) <= 300
        assert len(ref["excerpt"]) <= 500

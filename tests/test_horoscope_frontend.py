"""Phase 5: the UI contract and user interactions, without network or LLM calls."""
from unittest.mock import Mock, patch
from pathlib import Path

import pytest

from backend.app.schemas.horoscope import HoroscopeRequest


def request():
    return HoroscopeRequest(ngay=15, thang=8, nam=1995, chi_gio=5, provider="mock")


def test_report_contract_includes_chart_and_actual_prompt_sources():
    from backend.app.main import horoscope_read

    result = horoscope_read(request())
    assert result["status"] == "ok"
    assert len(result["la_so"]["thap_ni_cung"]) == 12
    assert "db" not in result["la_so"]
    assert result["meta"]["actual_provider"] == "mock"
    assert result["meta"]["is_mock"] is True
    assert len(result["citations"]) == result["meta"]["total_chunks_retrieved"]
    for citation in result["citations"]:
        assert citation["ref_id"] > 0
        assert citation["book_code"] in {"NPL", "DAU", "BD"}
        assert len(citation["excerpt"]) <= 500
        assert citation["verification_status"] == "unverified"
        assert "page_label" in citation


def test_missing_key_fallback_is_explicit():
    from backend.app.services import horoscope_interpreter as module

    with patch.object(module, "GEMINI_API_KEY", ""), patch.dict(module.os.environ, {"GEMINI_API_KEY": ""}):
        reading = module.interpret_horoscope({}, "", provider="auto")
    assert reading["_generation"]["is_mock"] is True
    assert reading["_generation"]["reason"] == "missing_key"


def test_invalid_calendar_date_is_rejected_before_api():
    from frontend.horoscope_view import validate_birth_date

    assert validate_birth_date(31, 2, 2000, True)
    assert validate_birth_date(31, 2, 2000, False)
    assert validate_birth_date(29, 2, 2001, True)
    assert validate_birth_date(29, 2, 2000, True) is None
    assert validate_birth_date(30, 2, 2000, False) is None


def test_chart_escapes_untrusted_text():
    from frontend.laso_renderer import luoi_html

    cell = {"cung_so": 1, "chuan_ten": "<script>bad</script>", "hanh_cung": "Thủy",
            "ten_cung": "Mệnh", "co_thanh": False, "tu_dai_han": None,
            "saos": [{"saoTen": '<img src=x onerror="bad()">', "saoLoai": 1}]}
    html = luoi_html([cell])
    assert "<script>" not in html
    assert "<img " not in html
    assert "&lt;script&gt;" in html


def test_ui_submit_validation_report_toggles_and_transport_error():
    from streamlit.testing.v1 import AppTest
    from backend.app.main import horoscope_read
    import requests

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend/horoscope_ui.py", default_timeout=20).run()
    assert not app.exception
    assert len(app.button) == 1
    # A calendar-invalid date must never reach the API.
    app.number_input(key="birth_day").set_value(31)
    app.number_input(key="birth_month").set_value(2)
    with patch("requests.post") as post:
        app.button[0].click().run()
        post.assert_not_called()
    assert app.error

    app.number_input(key="birth_day").set_value(15)
    app.number_input(key="birth_month").set_value(8)
    app.text_input(key="birth_name").set_value("Lê An")
    app.button_group(key="birth_topics").set_value(["tai_chinh"])
    payload = horoscope_read(request())
    payload["ho_ten"] = "Lê An"
    response = Mock()
    import json
    response.iter_lines.return_value = iter([
        json.dumps({'event': 'prepared', 'report': payload}),
        json.dumps({'event': 'progress', 'message': 'Đang thử', 'elapsed_ms': 10}),
        json.dumps({'event': 'result', 'report': payload}),
    ])
    with patch("requests.post", return_value=response) as post:
        app.button[0].click().run()
        assert post.call_args.kwargs["json"]["ho_ten"] == "Lê An"
    assert not app.exception
    assert any("Lê An" in item.value for item in app.markdown)
    assert app.tabs[0].label == "Tài chính"
    # Toggles rerun Streamlit, but must not regenerate a reading or call the API.
    with patch("requests.post") as post:
        app.toggle(key="show_chart").set_value(True).run()
        app.toggle(key="show_sources").set_value(True).run()
        post.assert_not_called()
    assert not app.exception
    with patch("requests.post", side_effect=requests.ConnectionError("offline")):
        app.button[0].click().run()
    assert app.error
    assert not app.exception
    assert any("Lê An" in item.value for item in app.markdown)  # last successful report survives


def _submit_mock_report(app, target_year: int | None = None):
    import json
    from backend.app.main import horoscope_read
    from tests.horoscope_support import make_request

    payload = horoscope_read(make_request(provider="mock", target_year=target_year))
    payload["ho_ten"] = "Lê An"
    response = Mock()
    response.iter_lines.return_value = iter([
        json.dumps({'event': 'prepared', 'report': payload}),
        json.dumps({'event': 'result', 'report': payload}),
    ])
    with patch("requests.post", return_value=response):
        if target_year is not None:
            app.number_input(key="target_year").set_value(target_year)
        app.button[0].click().run()
    assert not app.exception
    return payload


def test_changing_year_shows_resubmit_banner_without_calling_api():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend/horoscope_ui.py", default_timeout=20).run()
    payload = _submit_mock_report(app)
    report_year = payload["meta"]["target_year"]
    with patch("requests.post") as post:
        app.number_input(key="target_year").set_value(report_year + 1)
        app.run()
        post.assert_not_called()
    assert app.warning
    warning = " ".join(item.value for item in app.warning)
    assert str(report_year) in warning
    assert "tạo lại" in warning.lower()


def test_luu_nien_filter_renders_annual_star_table():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend/horoscope_ui.py", default_timeout=20).run()
    payload = _submit_mock_report(app)
    year = payload["meta"]["target_year"]
    options = list(app.selectbox(key="star_filter").options)
    target = next(option for option in options if option.startswith("Lưu niên"))
    assert str(year) in target
    app.selectbox(key="star_filter").set_value(target)
    app.run()
    assert not app.exception
    html = " ".join(item.value for item in app.markdown)
    assert "Lưu niên" in html
    assert "Thái Tuế" in html


def test_star_filter_resets_to_default_after_report_changes():
    """TC-21: bộ lọc 'Lưu niên năm X' và sao đã chọn được reset khi báo cáo mới (khác năm)."""
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend/horoscope_ui.py", default_timeout=20).run()
    payload = _submit_mock_report(app)
    year = payload["meta"]["target_year"]
    old_filter = next(o for o in app.selectbox(key="star_filter").options if o.startswith("Lưu niên"))
    app.selectbox(key="star_filter").set_value(old_filter)
    app.run()
    assert not app.exception

    new_payload = _submit_mock_report(app, target_year=year + 1)
    assert not app.exception
    assert app.selectbox(key="star_filter").value == "Cần lưu ý"
    assert new_payload["meta"]["target_year"] == year + 1
    assert not app.exception

# -*- coding: utf-8 -*-
"""Test Suite cho Hỏi nhanh theo chủ đề (/api/v1/horoscope/ask).

Nguyên tắc kiểm thử:
- Chạy offline (provider='mock'), không gọi mạng.
- Câu trả lời phải bám dữ kiện lá số + nguồn đã lấy; thiếu nguồn thì
  trả "Chưa đủ căn cứ từ nguồn đã lấy", không bịa.
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.schemas.horoscope import HoroscopeAskRequest
from backend.app.services import horoscope_ask
from backend.app.services.horoscope_ask import (
    ask_horoscope,
    ask_response_schema,
    mock_ask_answer,
    validate_ask,
)

BIRTH = dict(ngay=15, thang=8, nam=1995, chi_gio=5, gioi_tinh=1, duong_lich=True, target_year=2026)


def make_ask(topic: str = "tinh_cam", question: str = "Năm nay có người tìm hiểu không?",
             provider: str = "mock", **extra) -> HoroscopeAskRequest:
    return HoroscopeAskRequest(**BIRTH, topic=topic, question=question, provider=provider, **extra)


class TestAskSchema(unittest.TestCase):
    def test_schema_requires_question_and_valid_enum_fields(self):
        schema = ask_response_schema()
        self.assertEqual(set(schema["required"]), {
            "tra_loi", "muc_do_can_cu", "giai_thich_thun_viet", "fact_ids", "source_refs", "gioi_han",
        })
        self.assertIn("dau_hieu_ro", schema["properties"]["muc_do_can_cu"]["enum"])

    def test_empty_question_rejected(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            make_ask(question="")


class TestAskMockDeterministic(unittest.TestCase):
    def test_mock_is_deterministic_and_cites_real_sources(self):
        first = ask_horoscope(make_ask())
        second = ask_horoscope(make_ask())

        self.assertEqual(first["status"], "ok", msg=first)
        self.assertEqual(first["tra_loi"], second["tra_loi"])
        self.assertEqual(first["source_refs"], second["source_refs"])
        self.assertTrue(first["meta"]["is_mock"])
        self.assertEqual(first["meta"]["provider_used"], "mock")

        citation_ids = {c["ref_id"] for c in first["citations"]}
        self.assertTrue(set(first["source_refs"]) <= citation_ids)
        fact_ids = {f["fact_id"] for f in first["facts"]}
        self.assertTrue(set(first["fact_ids"]) <= fact_ids)
        self.assertIn(first["muc_do_can_cu"], {"dau_hieu_ro", "dau_hieu_yeu", "chua_du_can_cu"})
        self.assertTrue(first["giai_thich_thun_viet"].strip())
        self.assertTrue(first["citations"])
        self.assertTrue(all(c["verification_status"] == "unverified" for c in first["citations"]))

    def test_topic_tinh_cam_uses_phu_the_facts(self):
        result = ask_horoscope(make_ask(topic="tinh_cam", question="Năm nay có người tìm hiểu không?"))
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["facts"])
        self.assertTrue(all(f["cung"] == "Phu thê" for f in result["facts"]))
        self.assertIn("Phu thê", result["tra_loi"])

    def test_topic_tai_chinh_uses_tai_bach_facts(self):
        result = ask_horoscope(make_ask(topic="tai_chinh", question="Có giàu không?"))
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["facts"])
        self.assertTrue(all(f["cung"].casefold() == "tài bạch" for f in result["facts"]))

    def test_van_han_includes_annual_facts(self):
        result = ask_horoscope(make_ask(topic="van_han_hien_tai", question="Năm nay nên chú ý điều gì?"))
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["facts"])
        self.assertTrue(all(f["nhom"] == "luu_nien" for f in result["facts"]))
        self.assertEqual(result["topic"], "van_han")

    def test_invalid_topic_returns_error(self):
        result = ask_horoscope(make_ask(topic="khong_ton_tai"))
        self.assertEqual(result["status"], "error")
        self.assertIn("không hợp lệ", result["detail"])


class TestAskNoFabrication(unittest.TestCase):
    def test_no_sources_returns_chua_du_can_cu(self):
        raw = horoscope_ask.generate_raw_horoscope(
            BIRTH["ngay"], BIRTH["thang"], BIRTH["nam"], BIRTH["chi_gio"], BIRTH["gioi_tinh"], True,
        )
        features = horoscope_ask.extract_horoscope_features(raw, BIRTH["target_year"])
        answer = mock_ask_answer(features, [], [], "tinh_cam", "Năm nay có người tìm hiểu không?")
        self.assertEqual(answer["muc_do_can_cu"], "chua_du_can_cu")
        self.assertEqual(answer["source_refs"], [])
        self.assertIn("Chưa đủ căn cứ từ nguồn đã lấy", answer["tra_loi"])

    def test_ask_without_retrieved_sources_stays_honest(self):
        with patch.object(horoscope_ask, "build_ask_context", return_value=[]):
            result = ask_horoscope(make_ask())
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["muc_do_can_cu"], "chua_du_can_cu")
        self.assertEqual(result["source_refs"], [])
        self.assertEqual(result["citations"], [])
        self.assertIn("Chưa đủ căn cứ từ nguồn đã lấy", result["tra_loi"])


class TestAskValidation(unittest.TestCase):
    def _fact_map(self):
        return {"1": {"fact_id": "1", "source_refs": [1, 2]}}

    def _answer(self, **extra):
        base = {
            "tra_loi": "Theo dữ kiện, nên cân nhắc.",
            "muc_do_can_cu": "dau_hieu_ro",
            "giai_thich_thun_viet": "Cung Phu thê nói về quan hệ tình cảm.",
            "fact_ids": ["1"],
            "source_refs": [1],
            "gioi_han": "Chưa kiểm duyệt thủ công.",
        }
        base.update(extra)
        return base

    def test_valid_answer_passes(self):
        validate_ask(self._answer(), self._fact_map(), {1, 2})

    def test_fabricated_fact_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_ask(self._answer(fact_ids=["999"]), self._fact_map(), {1, 2})

    def test_fabricated_source_ref_rejected(self):
        with self.assertRaises(ValueError):
            validate_ask(self._answer(source_refs=[7]), self._fact_map(), {1, 2})

    def test_unlinked_source_ref_rejected(self):
        # ref 2 nằm trong allowed nhưng KHÔNG được liên kết tới fact_id "1" (chỉ link tới ref 1)
        with self.assertRaises(ValueError):
            validate_ask(
                self._answer(source_refs=[2]),
                {"1": {"fact_id": "1", "source_refs": [1]}},
                {1, 2},
            )

    def test_confident_answer_without_sources_rejected(self):
        with self.assertRaises(ValueError):
            validate_ask(self._answer(source_refs=[]), self._fact_map(), {1, 2})

    def test_chua_du_can_cu_allows_empty_sources(self):
        validate_ask(self._answer(muc_do_can_cu="chua_du_can_cu", source_refs=[]), self._fact_map(), {1, 2})

    def test_invalid_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_ask(self._answer(muc_do_can_cu="chac_chan"), self._fact_map(), {1, 2})


class TestAskEndpoint(unittest.TestCase):
    def test_endpoint_direct_returns_ok(self):
        from backend.app.main import horoscope_ask as endpoint
        result = endpoint(make_ask())
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["topic"], "tinh_cam")
        self.assertIn("citations", result)

    def test_auto_without_key_falls_back_to_mock(self):
        with patch.object(horoscope_ask, "GEMINI_API_KEY", ""), \
             patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            result = ask_horoscope(make_ask(provider="auto"))
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["meta"]["is_mock"])
        self.assertEqual(result["meta"]["reason"], "missing_key")


if __name__ == "__main__":
    unittest.main(verbosity=2)

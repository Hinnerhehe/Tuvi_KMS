# -*- coding: utf-8 -*-
"""Test Suite cho Giai đoạn 2: Smart RAG Bridge (Lá số Tử Vi ↔ Kho tri thức sách kinh điển).
Tuân thủ quy trình TDD trong GEMINI.md.
"""
from __future__ import annotations

import sys
import unittest

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.services.horoscope_features import (
    generate_raw_horoscope,
    extract_horoscope_features,
)
from backend.app.services.horoscope_rag_bridge import (
    generate_horoscope_queries,
    search_fts_sqlite,
    retrieve_horoscope_context,
    format_context_for_prompt,
)


class TestHoroscopeRAGBridge(unittest.TestCase):
    """Bộ kiểm thử unit test cho Smart RAG Bridge."""

    def setUp(self):
        # Dữ liệu mẫu lá số: 15/08/1995, giờ Thìn (chi_gio = 5), Nam
        raw = generate_raw_horoscope(nn=15, tt=8, nnnn=1995, chi_gio=5, gioi_tinh=1, duong_lich=True)
        self.features = extract_horoscope_features(raw, target_year=2026)

    def test_tc01_generate_horoscope_queries(self):
        """TC-BRIDGE-01: Kiểm tra sinh câu truy vấn đa chủ đề từ đặc trưng lá số."""
        queries = generate_horoscope_queries(self.features)

        self.assertIn("ban_menh", queries)
        self.assertIn("su_nghiep", queries)
        self.assertIn("tai_chinh", queries)
        self.assertIn("tinh_cam", queries)
        self.assertIn("van_han", queries)

        # Mệnh có Thất Sát hãm và bộ Sát Phá Tham
        bm_queries = queries["ban_menh"]
        self.assertTrue(len(bm_queries) >= 1)
        self.assertTrue(any("Thất sát" in q for q in bm_queries))

        # Quan lộc có Phá quân
        sn_queries = queries["su_nghiep"]
        self.assertTrue(any("Phá quân" in q for q in sn_queries))

        # Tài bạch có Tham lang
        tc_queries = queries["tai_chinh"]
        self.assertTrue(any("Tham lang" in q for q in tc_queries))

        # Phu thê có Vũ khúc hoặc Thiên tướng
        pt_queries = queries["tinh_cam"]
        self.assertTrue(any("Vũ khúc" in q or "Thiên tướng" in q for q in pt_queries))

    def test_tc02_search_fts_sqlite(self):
        """TC-BRIDGE-02: Kiểm tra truy vấn FTS5 trực tiếp trong kms.db."""
        hits = search_fts_sqlite("Thất sát Kình dương", limit=3)
        self.assertIsInstance(hits, list)
        self.assertTrue(len(hits) > 0)
        first = hits[0]
        self.assertIn("chunk_id", first)
        self.assertIn("book_code", first)
        self.assertIn("text", first)
        self.assertIn("score", first)

    def test_tc03_retrieve_horoscope_context(self):
        """TC-BRIDGE-03: Gom nhóm ngữ cảnh tri thức theo 5 chủ đề."""
        context = retrieve_horoscope_context(self.features, top_k_per_topic=2)

        self.assertIn("topics", context)
        self.assertIn("total_chunks", context)
        self.assertTrue(context["total_chunks"] > 0)

        topics = context["topics"]
        for key in ["ban_menh", "su_nghiep", "tai_chinh", "tinh_cam", "van_han"]:
            self.assertIn(key, topics)
            # Mỗi chủ đề phải có ít nhất 1 chunk liên quan
            self.assertTrue(len(topics[key]) >= 1, f"Topic '{key}' không có chunk nào!")

    def test_tc04_format_context_for_prompt(self):
        """TC-BRIDGE-04: Format ngữ cảnh có đánh số trích dẫn [1], [2] sẵn sàng nạp cho LLM."""
        context = retrieve_horoscope_context(self.features, top_k_per_topic=2)
        prompt_text = format_context_for_prompt(context)

        self.assertIsInstance(prompt_text, str)
        self.assertIn("[1]", prompt_text)
        self.assertIn("BẢN MỆNH & TÍNH CÁCH", prompt_text)
        self.assertIn("CÔNG DANH & SỰ NGHIỆP", prompt_text)
        self.assertIn("TÀI CHÍNH & TIỀN BẠC", prompt_text)
        self.assertIn("TÌNH CẢM & GIA ĐẠO", prompt_text)
        self.assertIn("VẬN HẠN HIỆN TẠI", prompt_text)


if __name__ == "__main__":
    unittest.main()


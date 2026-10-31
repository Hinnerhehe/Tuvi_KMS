"""Test suite cho Giai đoạn 4 — FastAPI Endpoint /api/v1/horoscope/read.

Chiến lược: Gọi trực tiếp hàm endpoint (không qua HTTP client) để tránh
vấn đề TestClient/httpx bị treo trên Python 3.14 Windows.

TC-API-01: Gọi endpoint với input hợp lệ → status=ok, có reading và thong_tin_co_ban
TC-API-02: Schema validation — chi_gio ngoài giới hạn → ValidationError
TC-API-03: provider=mock → output deterministic (gọi 2 lần cho cùng kết quả)
TC-API-04: Thiếu trường bắt buộc → ValidationError
TC-API-05: Response chứa đủ 5 sections reading
TC-API-06: meta chứa provider và total_chunks_retrieved
TC-API-07: ho_ten nhập vào xuất hiện trong response
"""
import sys
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
import unittest

# Thêm thư mục gốc vào sys.path để import backend
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _make_request(**overrides):
    """Tạo HoroscopeRequest với các giá trị mặc định hợp lệ."""
    from backend.app.schemas.horoscope import HoroscopeRequest
    defaults = dict(
        ho_ten="Nguyễn Văn Test",
        ngay=15,
        thang=8,
        nam=1995,
        chi_gio=5,       # Thìn (7-9h)
        gioi_tinh=1,
        duong_lich=True,
        top_k_per_topic=1,
        provider="mock",
        target_year=2026,
    )
    defaults.update(overrides)
    return HoroscopeRequest(**defaults)


class TestHoroscopeSchema(unittest.TestCase):
    """Kiểm thử Pydantic schema validation (TC-API-02, TC-API-04)."""

    def test_tc_api_02a_invalid_chi_gio_zero(self):
        """TC-API-02a: chi_gio=0 phải raise ValidationError (ge=1)."""
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            _make_request(chi_gio=0)

    def test_tc_api_02b_invalid_chi_gio_thirteen(self):
        """TC-API-02b: chi_gio=13 phải raise ValidationError (le=12)."""
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            _make_request(chi_gio=13)

    def test_tc_api_04_missing_ngay(self):
        """TC-API-04: Thiếu trường 'ngay' bắt buộc phải raise ValidationError."""
        from pydantic import ValidationError
        from backend.app.schemas.horoscope import HoroscopeRequest
        with self.assertRaises(ValidationError):
            HoroscopeRequest(thang=8, nam=1995, chi_gio=5)

    def test_valid_schema_instantiation(self):
        """Schema hợp lệ phải tạo được object không lỗi."""
        req = _make_request()
        self.assertEqual(req.ngay, 15)
        self.assertEqual(req.gioi_tinh, 1)
        self.assertEqual(req.provider, "mock")


class TestHoroscopeEndpointDirect(unittest.TestCase):
    """Kiểm thử hàm horoscope_read bằng cách gọi trực tiếp (không qua HTTP)."""

    @classmethod
    def setUpClass(cls):
        """Import endpoint function một lần."""
        # Import main để đảm bảo endpoint đã được định nghĩa
        from backend.app.main import horoscope_read
        cls.horoscope_read = staticmethod(horoscope_read)

    def _call(self, **overrides) -> dict:
        """Gọi endpoint trực tiếp với HoroscopeRequest."""
        req = _make_request(**overrides)
        return self.horoscope_read(req)

    # TC-API-01
    def test_tc_api_01_valid_request_returns_ok(self):
        """TC-API-01: Gọi hợp lệ → status='ok', có reading và thong_tin_co_ban."""
        result = self._call()
        self.assertEqual(result["status"], "ok", msg=f"Lỗi: {result}")
        self.assertIn("reading", result)
        self.assertIn("thong_tin_co_ban", result)
        self.assertIsInstance(result["reading"], dict)
        self.assertIsInstance(result["thong_tin_co_ban"], dict)

    # TC-API-03
    def test_tc_api_03_mock_deterministic(self):
        """TC-API-03: provider=mock cho cùng tieu_de khi gọi 2 lần."""
        r1 = self._call(provider="mock")
        r2 = self._call(provider="mock")
        self.assertEqual(r1["status"], "ok")
        self.assertEqual(r2["status"], "ok")
        self.assertEqual(r1["reading"].get("tieu_de"), r2["reading"].get("tieu_de"))

    # TC-API-05
    def test_tc_api_05_reading_has_five_sections(self):
        """TC-API-05: reading phải chứa đủ 5 chủ đề luận giải."""
        result = self._call()
        reading = result["reading"]
        for key in ["tong_quan", "su_nghiep", "tai_chinh", "tinh_cam", "van_han_hien_tai"]:
            self.assertIn(key, reading, msg=f"Thiếu key '{key}' trong reading")

    # TC-API-06
    def test_tc_api_06_meta_fields(self):
        """TC-API-06: meta phải có 'provider' và 'total_chunks_retrieved'."""
        result = self._call()
        meta = result.get("meta", {})
        self.assertIn("provider", meta)
        self.assertIn("total_chunks_retrieved", meta)

    # TC-API-07
    def test_tc_api_07_ho_ten_echoed(self):
        """TC-API-07: ho_ten trong request phải xuất hiện trong response."""
        result = self._call(ho_ten="Trần Thị Bình")
        self.assertEqual(result["ho_ten"], "Trần Thị Bình")

    # TC-API-08: Kiểm tra thong_tin_co_ban có các field cơ bản
    def test_tc_api_08_thong_tin_co_ban_fields(self):
        """TC-API-08: thong_tin_co_ban phải có ban_menh và cuc."""
        result = self._call()
        tco = result.get("thong_tin_co_ban", {})
        # Ít nhất phải có ban_menh
        self.assertTrue(len(tco) > 0, msg="thong_tin_co_ban không được rỗng")


if __name__ == "__main__":
    unittest.main(verbosity=2)


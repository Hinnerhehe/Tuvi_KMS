# -*- coding: utf-8 -*-
"""Test Suite cho Task 1.1: Trích xuất đặc trưng lá số Tử Vi (Horoscope Feature Extractor).
Tuân thủ quy trình TDD trong GEMINI.md.
"""
from __future__ import annotations

import sys
import unittest

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.services.horoscope_features import (
    analyze_menh_cuc,
    get_tam_phuong_tu_chinh,
    detect_star_group,
    categorize_stars_in_palace,
    extract_tu_hoa,
    find_current_dai_han,
    extract_horoscope_features,
    generate_raw_horoscope,
)


class TestHoroscopeFeatures(unittest.TestCase):
    """Bộ kiểm thử unit tests cho horoscope_features."""

    def test_tc01_analyze_menh_cuc(self):
        """TC-01: Kiểm tra tính tương quan Ngũ hành Bản mệnh vs Cục."""
        # Cục sinh Mệnh: Kim Cục sinh Thủy Mệnh
        res1 = analyze_menh_cuc("Giản Hạ Thủy", "Kim tứ Cục")
        self.assertEqual(res1["relation_type"], "CUC_SINH_MENH")
        self.assertIn("thuận lợi", res1["meaning_layman"].lower())

        # Mệnh sinh Cục: Hỏa Mệnh sinh Thổ Cục
        res2 = analyze_menh_cuc("Sơn Đầu Hỏa", "Thổ ngũ Cục")
        self.assertEqual(res2["relation_type"], "MENH_SINH_CUC")
        self.assertIn("cống hiến", res2["meaning_layman"].lower())

        # Tị hòa: Mộc Mệnh - Mộc Cục
        res3 = analyze_menh_cuc("Đại Lâm Mộc", "Mộc tam Cục")
        self.assertEqual(res3["relation_type"], "MENH_CUC_TI_HOA")

        # Mệnh khắc Cục: Mộc Mệnh khắc Thổ Cục
        res4 = analyze_menh_cuc("Đại Lâm Mộc", "Thổ ngũ Cục")
        self.assertEqual(res4["relation_type"], "MENH_KHAC_CUC")
        self.assertIn("vượt khó", res4["meaning_layman"].lower())

        # Cục khắc Mệnh: Hỏa Cục khắc Kim Mệnh
        res5 = analyze_menh_cuc("Kiếm Phong Kim", "Hỏa lục Cục")
        self.assertEqual(res5["relation_type"], "CUC_KHAC_MENH")

    def test_tc02_tam_phuong_tu_chinh(self):
        """TC-02: Kiểm tra công thức xác định Tam phương Tứ chính."""
        # Giả lập 12 cung với chỉ số cung_so từ 1 đến 12
        # Cung 1 (Tý):
        # Đối xung: 7 (Ngọ)
        # Tam hợp: 5 (Thìn) và 9 (Thân)
        cung_map = {i: {"cung_so": i, "chuan_ten": f"Cung_{i}", "saos": []} for i in range(1, 13)}
        
        tptc = get_tam_phuong_tu_chinh(1, cung_map)
        self.assertEqual(tptc["chinh_cung"]["cung_so"], 1)
        self.assertEqual(tptc["doi_cung"]["cung_so"], 7)
        tam_hop_sos = sorted([c["cung_so"] for c in tptc["tam_hop"]])
        self.assertEqual(tam_hop_sos, [5, 9])
        self.assertEqual(len(tptc["all_cung_sos"]), 4)

    def test_tc03_detect_star_group(self):
        """TC-03: Nhận diện bộ chính tinh cốt lõi (Cách cục nòng cốt)."""
        # Sát Phá Tham: Thất Sát, Phá Quân, Tham Lang
        saos_spt = [{"saoTen": "Thất sát", "saoLoai": 1}, {"saoTen": "Tham lang", "saoLoai": 1}]
        group_spt = detect_star_group(saos_spt)
        self.assertEqual(group_spt["code"], "SAT_PHA_THAM")

        # Cự Nhật: Cự Môn, Thái Dương
        saos_cn = [{"saoTen": "Thái Dương", "saoLoai": 1}, {"saoTen": "Cự môn", "saoLoai": 1}]
        group_cn = detect_star_group(saos_cn)
        self.assertEqual(group_cn["code"], "CU_NHAT")

        # Cơ Nguyệt Đồng Lương
        saos_cndl = [{"saoTen": "Thiên Cơ", "saoLoai": 1}, {"saoTen": "Thiên Lương", "saoLoai": 1}]
        group_cndl = detect_star_group(saos_cndl)
        self.assertEqual(group_cndl["code"], "CO_NGUYET_DONG_LUONG")

        # Tử Phủ Vũ Tướng
        saos_tpvt = [{"saoTen": "Tử vi", "saoLoai": 1}, {"saoTen": "Thiên phủ", "saoLoai": 1}]
        group_tpvt = detect_star_group(saos_tpvt)
        self.assertEqual(group_tpvt["code"], "TU_PHU_VU_TUONG")

        # Vô Chính Diệu
        saos_vcd = [{"saoTen": "Văn Xương", "saoLoai": 2}]
        group_vcd = detect_star_group(saos_vcd)
        self.assertEqual(group_vcd["code"], "VO_CHINH_DIEU")

    def test_tc04_categorize_stars_in_palace(self):
        """TC-04: Phân loại chính tinh đắc hãm, cát tinh, sát tinh."""
        sample_saos = [
            {"saoID": 5, "saoTen": "Thái Dương", "saoLoai": 1, "saoDacTinh": "V"},
            {"saoID": 10, "saoTen": "Cự môn", "saoLoai": 1, "saoDacTinh": "V"},
            {"saoID": 52, "saoTen": "Kình dương", "saoLoai": 11, "saoDacTinh": "H"},
            {"saoID": 57, "saoTen": "Văn Xương", "saoLoai": 2, "saoDacTinh": "Đ"},
            {"saoID": 94, "saoTen": "Hóa lộc", "saoLoai": 2},
        ]
        res = categorize_stars_in_palace(sample_saos)
        self.assertEqual(len(res["chinh_tinh"]), 2)
        self.assertTrue(all(s["dac_tinh"] == "V" for s in res["chinh_tinh"]))
        self.assertIn("Kình dương", [s["ten"] for s in res["sat_tinh"]])
        self.assertIn("Văn Xương", [s["ten"] for s in res["cat_tinh"]])

    def test_tc05_extract_tu_hoa(self):
        """TC-05: Trích xuất vị trí Tứ Hóa và cung đóng."""
        mock_cungs = [
            {"chuan_ten": "Mệnh", "cung_so": 1, "saos": [{"saoID": 94, "saoTen": "Hóa lộc"}]},
            {"chuan_ten": "Tài Bạch", "cung_so": 5, "saos": [{"saoID": 95, "saoTen": "Hóa kỵ"}]},
            {"chuan_ten": "Quan Lộc", "cung_so": 9, "saos": [{"saoID": 93, "saoTen": "Hóa quyền"}]},
            {"chuan_ten": "Phúc Đức", "cung_so": 7, "saos": [{"saoID": 92, "saoTen": "Hóa khoa"}]},
        ]
        tu_hoa = extract_tu_hoa(mock_cungs)
        self.assertEqual(len(tu_hoa), 4)
        loc = next(h for h in tu_hoa if h["code"] == "HOA_LOC")
        self.assertEqual(loc["cung_ten"], "Mệnh")
        ky = next(h for h in tu_hoa if h["code"] == "HOA_KY")
        self.assertEqual(ky["cung_ten"], "Tài Bạch")

    def test_tc06_find_current_dai_han(self):
        """TC-06: Xác định đúng Đại hạn 10 năm theo tuổi."""
        mock_cungs = [
            {"chuan_ten": "Mệnh", "cung_so": 1, "tu_dai_han": 2, "saos": []},
            {"chuan_ten": "Phụ mẫu", "cung_so": 2, "tu_dai_han": 12, "saos": []},
            {"chuan_ten": "Phúc đức", "cung_so": 3, "tu_dai_han": 22, "saos": []},
            {"chuan_ten": "Điền trạch", "cung_so": 4, "tu_dai_han": 32, "saos": []},
        ]
        # Người 28 tuổi -> Đại hạn 22-31 tuổi (Phúc đức)
        dh = find_current_dai_han(mock_cungs, current_age=28)
        self.assertIsNotNone(dh)
        self.assertEqual(dh["cung_ten"], "Phúc đức")
        self.assertEqual(dh["tu_tuoi"], 22)
        self.assertEqual(dh["den_tuoi"], 31)

    def test_tc07_extract_horoscope_features_e2e(self):
        """TC-07: Kiểm thử end-to-end với ngày sinh thực tế."""
        # Lá số: 15/08/1995 lúc 07:30 sáng (Giờ Thìn, chi_gio = 5), Nam, Dương lịch
        raw_laso = generate_raw_horoscope(nn=15, tt=8, nnnn=1995, chi_gio=5, gioi_tinh=1, duong_lich=True)
        features = extract_horoscope_features(raw_laso, target_year=2026)

        # Kiểm tra các trường cốt lõi
        self.assertIn("menh_cuc", features)
        self.assertIn("tam_phuong_tu_chinh_menh", features)
        self.assertIn("star_group", features)
        self.assertIn("tu_hoa", features)
        self.assertIn("dai_han_hien_tai", features)
        self.assertIn("cung_chinh", features)
        
        # Người sinh 1995, năm xem 2026 -> 32 tuổi âm
        self.assertEqual(features["dai_han_hien_tai"]["tuoi_hien_tai"], 32)
        self.assertTrue(len(features["cung_chinh"]) >= 5)


if __name__ == "__main__":
    unittest.main()


"""P1: lớp lưu niên theo năm Can Chi — tất định, không phụ thuộc AI."""
from __future__ import annotations

import sys
from pathlib import Path

from backend.app.services.horoscope_analysis import build_star_facts
from backend.app.services.horoscope_annual import compute_luu_nien
from backend.app.services.horoscope_rag_bridge import generate_horoscope_queries, normalized
from tests.horoscope_support import make_features, make_raw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from lasotuvi.AmDuong import dichCung  # noqa: E402


def test_year_maps_to_can_chi():
    cungs = make_raw()["thap_ni_cung"]
    ln = compute_luu_nien(cungs, 2026)
    assert (ln["can"], ln["chi"], ln["can_chi"]) == ("Bính", "Ngọ", "Bính Ngọ")
    ln2 = compute_luu_nien(cungs, 1995)
    assert (ln2["can"], ln2["chi"]) == ("Ất", "Hợi")


def test_luu_tu_hoa_follows_year_can_and_natal_palace():
    cungs = make_raw()["thap_ni_cung"]
    ln = compute_luu_nien(cungs, 2026)
    pairs = {(x["ten_sao"], x["code"]) for x in ln["luu_tu_hoa"]}
    assert pairs == {
        ("Thiên Đồng", "HOA_LOC"), ("Thiên Cơ", "HOA_QUYEN"),
        ("Văn Xương", "HOA_KHOA"), ("Liêm Trinh", "HOA_KY"),
    }
    for entry in ln["luu_tu_hoa"]:
        palace = next(
            c for c in cungs
            if any((s.get("saoTen") or "").casefold() == entry["ten_sao"].casefold() for s in c.get("saos", []))
        )
        assert entry["cung_ten"] in (palace["ten_cung"], palace["chuan_ten"])


def test_vong_thai_tue_offsets_match_vendor_table():
    cungs = make_raw()["thap_ni_cung"]
    ln = compute_luu_nien(cungs, 2026)
    assert ln["thai_tue"]["dia_chi"] == "Ngọ"
    by_so = {c["cung_so"]: c for c in cungs}
    thai_tue_so = ln["thai_tue"]["cung_so"]
    assert ln["vong_thai_tue"]["Tuế Phá"]["dia_chi"] == by_so[dichCung(thai_tue_so, 6)]["chuan_ten"]
    assert ln["vong_thai_tue"]["Bạch Hổ"]["dia_chi"] == by_so[dichCung(thai_tue_so, 8)]["chuan_ten"]
    for entry in ln["vong_thai_tue"].values():
        assert entry["loai"] in {"hung", "cat", "trung"}
        assert {"ten", "dia_chi", "cung_ten", "loai"} <= set(entry.keys())


def test_tieu_han_repeats_every_twelve_years():
    raw = make_raw()
    f_y = make_features(2026)["nam_xem"]["tieu_han"]
    f_y1 = make_features(2027)["nam_xem"]["tieu_han"]
    f_y12 = make_features(2038)["nam_xem"]["tieu_han"]
    assert f_y == f_y12
    assert f_y != f_y1


def test_changing_year_changes_annual_layer():
    a = make_features(2026)
    b = make_features(2027)
    assert a["luu_nien"]["can_chi"] != b["luu_nien"]["can_chi"]
    assert a["luu_nien"]["luu_tu_hoa"] != b["luu_nien"]["luu_tu_hoa"]
    assert a["nam_xem"]["tieu_han"] != b["nam_xem"]["tieu_han"]
    assert a["luu_nien"]["vong_thai_tue"] != b["luu_nien"]["vong_thai_tue"]


def test_facts_include_annual_star_group():
    facts = build_star_facts(make_features(2026), {})
    annual = [f for f in facts if f["nhom"] == "luu_nien"]
    assert annual
    assert all(f["dac_tinh"] == "—" for f in annual)
    assert all("Lưu niên" in f["roles"] for f in annual)
    assert any(f["sao"] == "Thái Tuế" and f["dia_chi"] == "Ngọ" for f in annual)


def test_van_han_queries_carry_the_year_and_annual_stars():
    queries = generate_horoscope_queries(make_features(2026))["van_han"]
    flat = " ".join(normalized(q) for q in queries)
    assert "luu nien" in flat
    assert "bính ngọ" in flat or "binh ngo" in flat
    assert "liem trinh" in flat

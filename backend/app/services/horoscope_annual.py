# -*- coding: utf-8 -*-
"""An lưu niên theo năm Can Chi: vòng Thái Tuế và lưu Tứ Hóa.

Quy tắc tham chiếu vendor/lasotuvi/App.py:
- Vòng Thái Tuế: 12 sao, offset tính từ cung Thái Tuế (App.py dòng 150-185).
- Bảng Tứ Hóa theo 10 thiên can (App.py dòng 402-451).

Đây là lớp dữ kiện tất định (không gọi AI): dùng để hiển thị ngay cho người xem
và làm đầu vào cho phần luận giải. Các sao lưu niên chỉ để tham khảo, chiêm nghiệm;
không phải dự báo sự kiện.
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
VENDOR_PATH = ROOT / "vendor"
if str(VENDOR_PATH) not in sys.path:
    sys.path.insert(0, str(VENDOR_PATH))

from lasotuvi.AmDuong import diaChi, dichCung, thienCan  # noqa: E402

TU_HOA_CODES = ("HOA_LOC", "HOA_QUYEN", "HOA_KHOA", "HOA_KY")
TU_HOA_NAMES = {
    "HOA_LOC": "Hóa lộc",
    "HOA_QUYEN": "Hóa quyền",
    "HOA_KHOA": "Hóa khoa",
    "HOA_KY": "Hóa kỵ",
}

# Bảng Tứ Hóa theo can năm. Nguồn: vendor/lasotuvi/App.py dòng 402-451.
TU_HOA_BY_CAN: dict[str, dict[str, str]] = {
    "Giáp": {"HOA_LOC": "Liêm Trinh", "HOA_QUYEN": "Phá Quân", "HOA_KHOA": "Vũ Khúc", "HOA_KY": "Thái Dương"},
    "Ất": {"HOA_LOC": "Thiên Cơ", "HOA_QUYEN": "Thiên Lương", "HOA_KHOA": "Tử Vi", "HOA_KY": "Thái Âm"},
    "Bính": {"HOA_LOC": "Thiên Đồng", "HOA_QUYEN": "Thiên Cơ", "HOA_KHOA": "Văn Xương", "HOA_KY": "Liêm Trinh"},
    "Đinh": {"HOA_LOC": "Thái Âm", "HOA_QUYEN": "Thiên Đồng", "HOA_KHOA": "Thiên Cơ", "HOA_KY": "Cự Môn"},
    "Mậu": {"HOA_LOC": "Tham Lang", "HOA_QUYEN": "Thái Âm", "HOA_KHOA": "Hữu Bật", "HOA_KY": "Thiên Cơ"},
    "Kỷ": {"HOA_LOC": "Vũ Khúc", "HOA_QUYEN": "Tham Lang", "HOA_KHOA": "Thiên Lương", "HOA_KY": "Văn Khúc"},
    "Canh": {"HOA_LOC": "Thái Dương", "HOA_QUYEN": "Vũ Khúc", "HOA_KHOA": "Thiên Đồng", "HOA_KY": "Thái Âm"},
    "Tân": {"HOA_LOC": "Cự Môn", "HOA_QUYEN": "Thái Dương", "HOA_KHOA": "Văn Khúc", "HOA_KY": "Văn Xương"},
    "Nhâm": {"HOA_LOC": "Thiên Lương", "HOA_QUYEN": "Tử Vi", "HOA_KHOA": "Thiên Phủ", "HOA_KY": "Vũ Khúc"},
    "Quý": {"HOA_LOC": "Phá Quân", "HOA_QUYEN": "Cự Môn", "HOA_KHOA": "Thái Âm", "HOA_KY": "Tham Lang"},
}

# (tên sao, offset từ Thái Tuế, phân loại). Nguồn: vendor/lasotuvi/App.py dòng 150-185.
VONG_THAI_TUE: tuple[tuple[str, int, str], ...] = (
    ("Thái Tuế", 0, "trung"),
    ("Thiếu Dương", 1, "trung"),
    ("Tang Môn", 2, "hung"),
    ("Thiếu Âm", 3, "trung"),
    ("Quan Phù", 4, "cat"),
    ("Tử Phủ", 5, "cat"),
    ("Tuế Phá", 6, "hung"),
    ("Long Đức", 7, "cat"),
    ("Bạch Hổ", 8, "hung"),
    ("Phúc Đức", 9, "cat"),
    ("Điếu Khách", 10, "cat"),
    ("Trực Phù", 11, "cat"),
)

CAUTION_STARS = ("Thái Tuế", "Tuế Phá", "Bạch Hổ", "Tang Môn")

METHOD = (
    "An lưu niên theo vòng Thái Tuế (12 sao) và lưu Tứ Hóa theo can năm, "
    "đối chiếu bảng an sao của vendor/lasotuvi/App.py."
)
LIMITATIONS = (
    "Chỉ an vòng Thái Tuế và lưu Tứ Hóa; chưa an các lưu tinh khác. "
    "Dùng để tham khảo và chiêm nghiệm, không phải dự báo sự kiện."
)


def _strip_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", value or "") if unicodedata.category(c) != "Mn"
    ).lower()


def can_chi_of_year(year: int) -> tuple[str, str]:
    """Trả về (can, chi) của năm âm lịch. 2026 -> ("Bính", "Ngọ")."""
    can = thienCan[(year - 4) % 10 + 1]["tenCan"]
    chi = diaChi[(year - 4) % 12 + 1]["tenChi"]
    return can, chi


def tu_hoa_stars_for_can(can: str) -> dict[str, str]:
    """Bốn sao nhận Tứ Hóa theo can (map code -> tên sao gốc)."""
    return TU_HOA_BY_CAN.get(can, {})


def _find_star_palace(cungs: list[dict[str, Any]], star_name: str) -> dict[str, Any] | None:
    """Tìm cung đang chứa sao gốc theo tên (ưu tiên khớp chính xác, sau đó bỏ dấu)."""
    target = (star_name or "").casefold()
    for cung in cungs:
        for sao in cung.get("saos", []):
            if (sao.get("saoTen") or "").casefold() == target:
                return cung
    target_norm = _strip_accents(star_name)
    for cung in cungs:
        for sao in cung.get("saos", []):
            if _strip_accents(sao.get("saoTen") or "") == target_norm:
                return cung
    return None


def _palace_brief(cung: dict[str, Any] | None, star_name: str) -> dict[str, Any]:
    if not cung:
        return {
            "ten": star_name,
            "cung_so": None,
            "cung_ten": "",
            "chuan_ten": "",
            "dia_chi": "",
        }
    return {
        "ten": star_name,
        "cung_so": cung.get("cung_so"),
        "cung_ten": cung.get("ten_cung") or cung.get("chuan_ten", ""),
        "chuan_ten": cung.get("chuan_ten", ""),
        "dia_chi": cung.get("chuan_ten", ""),
    }


def compute_luu_nien(
    thap_ni_cung: list[dict[str, Any]],
    year: int,
    cung_menh_so: int | None = None,
    cung_than_so: int | None = None,
    dai_han_cung_so: int | None = None,
    tieu_han_cung_so: int | None = None,
) -> dict[str, Any]:
    """An lưu niên cho một năm: Can Chi, vòng Thái Tuế, lưu Tứ Hóa và cờ cần lưu ý."""
    can, chi = can_chi_of_year(year)
    by_cung_so = {c.get("cung_so"): c for c in thap_ni_cung}
    thai_tue_cung = next((c for c in thap_ni_cung if c.get("chuan_ten") == chi), None)

    vong: dict[str, dict[str, Any]] = {}
    if thai_tue_cung:
        for star_name, offset, loai in VONG_THAI_TUE:
            cung_so = dichCung(thai_tue_cung["cung_so"], offset)
            entry = _palace_brief(by_cung_so.get(cung_so), star_name)
            entry["loai"] = loai
            vong[star_name] = entry

    luu_tu_hoa: list[dict[str, Any]] = []
    for code in TU_HOA_CODES:
        star_name = TU_HOA_BY_CAN[can][code]
        cung = _find_star_palace(thap_ni_cung, star_name)
        entry = _palace_brief(cung, star_name)
        entry.update({"ten_sao": star_name, "code": code, "ten": TU_HOA_NAMES[code]})
        luu_tu_hoa.append(entry)

    roles: list[tuple[str, int]] = []
    if cung_menh_so:
        roles.append(("menh", cung_menh_so))
    if cung_than_so:
        roles.append(("than", cung_than_so))
    if dai_han_cung_so:
        roles.append(("dai_han", dai_han_cung_so))
    if tieu_han_cung_so:
        roles.append(("tieu_han", tieu_han_cung_so))

    hits: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add_hit(star: str, cung_so: int | None, role: str, cung_ten: str) -> None:
        key = (star, role)
        if cung_so is None or key in seen:
            return
        seen.add(key)
        hits.append({"sao": star, "cung_ten": cung_ten, "don_vai": role})

    for star_name in CAUTION_STARS:
        entry = vong.get(star_name)
        if not entry:
            continue
        for role, cung_so in roles:
            if entry.get("cung_so") == cung_so:
                add_hit(star_name, cung_so, role, entry.get("cung_ten", ""))

    for entry in luu_tu_hoa:
        if entry["code"] != "HOA_KY":
            continue
        for role, cung_so in roles:
            if entry.get("cung_so") == cung_so:
                add_hit(f"{entry['ten_sao']} lưu Kỵ", cung_so, role, entry.get("cung_ten", ""))

    if not hits:
        level = "nhan"
    elif len(hits) >= 2 or any(hit["don_vai"] in ("menh", "than") for hit in hits):
        level = "nang"
    else:
        level = "vua"

    return {
        "year": year,
        "can": can,
        "chi": chi,
        "can_chi": f"{can} {chi}",
        "thai_tue": _palace_brief(thai_tue_cung, "Thái Tuế"),
        "vong_thai_tue": vong,
        "luu_tu_hoa": luu_tu_hoa,
        "can_luu_y": {
            "count": len(hits),
            "level": level,
            "hits": hits,
            "method": METHOD,
            "limitations": LIMITATIONS,
        },
        "method": METHOD,
        "limitations": LIMITATIONS,
    }

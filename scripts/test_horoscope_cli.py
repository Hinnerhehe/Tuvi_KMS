# -*- coding: utf-8 -*-
"""Script kiểm thử toàn diện Pipeline Luận giải Tử Vi (Trực quan trên Terminal).

Cách chạy:
    python scripts/test_horoscope_cli.py
Hoặc truyền tham số:
    python scripts/test_horoscope_cli.py --ngay 15 --thang 8 --nam 1995 --gio 5 --gioi_tinh 1 --provider mock
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Đảm bảo UTF-8 cho console Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.horoscope_features import (
    generate_raw_horoscope,
    extract_horoscope_features,
)
from backend.app.services.horoscope_rag_bridge import (
    generate_horoscope_queries,
    retrieve_horoscope_context,
    format_context_for_prompt,
)
from backend.app.services.horoscope_interpreter import interpret_horoscope, HoroscopeGenerationError

CHI_GIO_MAP = {
    1: "Tý (23:00 - 01:00)",
    2: "Sửu (01:00 - 03:00)",
    3: "Dần (03:00 - 05:00)",
    4: "Mão (05:00 - 07:00)",
    5: "Thìn (07:00 - 09:00)",
    6: "Tỵ (09:00 - 11:00)",
    7: "Ngọ (11:00 - 13:00)",
    8: "Mùi (13:00 - 15:00)",
    9: "Thân (15:00 - 17:00)",
    10: "Dậu (17:00 - 19:00)",
    11: "Tuất (19:00 - 21:00)",
    12: "Hợi (21:00 - 23:00)",
}


def print_separator(title="", char="=", length=75):
    if title:
        side_len = max(2, (length - len(title) - 2) // 2)
        print(f"\n{char * side_len} {title} {char * side_len}")
    else:
        print(char * length)


def run_pipeline_test(
    ho_ten: str = "Người Thử Nghiệm",
    ngay: int = 15,
    thang: int = 8,
    nam: int = 1995,
    chi_gio: int = 5,
    gioi_tinh: int = 1,
    duong_lich: bool = True,
    target_year: int = 2026,
    provider: str = "mock",
    top_k: int = 1,
):
    gio_label = CHI_GIO_MAP.get(chi_gio, f"Giờ {chi_gio}")
    gioi_tinh_str = "Nam (Dương Nam)" if gioi_tinh == 1 else "Nữ (Âm Nữ)"

    print_separator("🔍 BẮT ĐẦU TEST LUỒNG TỬ VI TOÀN DIỆN")
    print(f"👤 Người xem:    {ho_ten}")
    print(f"📅 Ngày sinh:    {ngay:02d}/{thang:02d}/{nam} ({'Dương lịch' if duong_lich else 'Âm lịch'})")
    print(f"⏰ Giờ sinh:     {gio_label}")
    print(f"⚧ Giới tính:    {gioi_tinh_str}")
    print(f"🎯 Năm xem hạn:  {target_year}")
    print(f"🤖 LLM Provider: {provider}")

    # BƯỚC 1: LẬP LÁ SỐ & TRÍCH XUẤT ĐẶC TRƯNG
    print_separator("1️⃣ BÓC TÁCH ĐẶC TRƯNG LÁ SỐ (FEATURE EXTRACTION)", "-")
    raw_laso = generate_raw_horoscope(ngay, thang, nam, chi_gio, gioi_tinh, duong_lich)
    features = extract_horoscope_features(raw_laso, target_year=target_year)

    co_ban = features["thong_tin_co_ban"]
    menh_cuc = features["menh_cuc"]
    star_group = features["star_group"]
    dai_han = features.get("dai_han_hien_tai") or {}

    print(f"• Năm Can Chi:       {co_ban['can_chi_nam']}")
    print(f"• Bản Mệnh:          {co_ban['ban_menh']}")
    print(f"• Cục số:            {co_ban['ten_cuc']}")
    print(f"• Tương quan Mệnh-Cục: {menh_cuc['title']} ({menh_cuc['hanh_menh']} vs {menh_cuc['hanh_cuc']})")
    print(f"  Ý nghĩa bình dân:   \"{menh_cuc['meaning_layman']}\"")
    print(f"• Cung Mệnh cư:      {co_ban['cung_menh']}")
    print(f"• Cung Thân cư:      {co_ban['cung_than']}")
    print(f"• Bộ cách cục chính: {star_group['name']} ({star_group['code']})")
    print(f"  Mô tả:              \"{star_group.get('layman', '')}\"")
    
    menh_stars = features.get("menh_stars", {})
    chinh_tinh = [f"{s['ten']} ({s['dac_tinh']})" for s in menh_stars.get("chinh_tinh", [])]
    sat_tinh = [s["ten"] for s in menh_stars.get("sat_tinh", [])]
    cat_tinh = [s["ten"] for s in menh_stars.get("cat_tinh", [])]
    print(f"• Sao tại Mệnh:      Chính tinh: {', '.join(chinh_tinh) or 'Vô chính diệu'}")
    if sat_tinh:
        print(f"                     Sát tinh:   {', '.join(sat_tinh)}")
    if cat_tinh:
        print(f"                     Cát tinh:   {', '.join(cat_tinh)}")

    tuoi_am = features['nam_xem']['tuoi_am']
    tu_tuoi = dai_han.get("tu_tuoi", "")
    den_tuoi = dai_han.get("den_tuoi", "")
    cung_dh = dai_han.get("cung_ten", "")
    linh_vuc_dh = dai_han.get("ten_linh_vuc", "")
    chinh_dh = dai_han.get("chinh_tinh", "")
    print(f"• Đại hạn hiện tại:  {tu_tuoi} - {den_tuoi} tuổi tại cung {cung_dh} ({linh_vuc_dh}) | Sao: {chinh_dh} (Tuổi âm: {tuoi_am})")

    # BƯỚC 2: RAG SEARCH TỪ 3 CUỐN SÁCH
    print_separator("2️⃣ KHO TRI THỨC SÁCH NGUỒN (SMART RAG RETRIEVAL)", "-")
    queries = generate_horoscope_queries(features)
    print("📌 Câu truy vấn tự động sinh ra cho 5 chủ đề:")
    for topic, q in queries.items():
        print(f"  [{topic}]: '{q}'")

    context = retrieve_horoscope_context(features, top_k_per_topic=top_k)
    print(f"\n📚 Tổng số đoạn trích tìm thấy trong kms.db: {context['total_chunks']} đoạn.")
    for topic, items in context["topics"].items():
        print(f"\n  ➤ Chủ đề [{topic}] ({len(items)} đoạn trích):")
        for it in items:
            excerpt = it['text'].replace('\n', ' ')[:100] + "..."
            print(f"    - [{it['ref_id']}] Sách {it['book_code']} | Chương: {it.get('chapter', 'Chung')}")
            print(f"      Trích: \"{excerpt}\"")

    # BƯỚC 3: AI LUẬN GIẢI
    print_separator("3️⃣ BÀI LUẬN GIẢI THỰC TẾ CHO NGƯỜI DÙNG (AI READING)", "-")
    formatted_ctx = format_context_for_prompt(context)
    try:
        reading = interpret_horoscope(features, formatted_ctx, provider=provider, context=context)
    except HoroscopeGenerationError as exc:
        print(f"AI chưa tạo được bài đọc ({exc.code}): {exc}")
        return
    generation = reading.pop('_generation')
    print(f"Chế độ thực chạy: {generation['actual_provider']} | Model: {generation['model']} | {generation['elapsed_ms'] / 1000:.2f}s")
    if generation.get('message'):
        print(generation['message'])

    print(f"\n✨ {reading.get('tieu_de', 'BÀI LUẬN GIẢI TỬ VI')}\n")

    tq = reading.get("tong_quan", {})
    print("【 1. TỔNG QUAN TÍNH CÁCH & BẢN SẮC 】")
    print(f"  • Bản sắc: {tq.get('ban_sac', '')}")
    print("  • Điểm mạnh cốt lõi:")
    for dm in tq.get("diem_manh", []):
        print(f"    + {dm}")
    print("  • Điểm cần rèn luyện:")
    for dr in tq.get("diem_can_ren_luyen", []):
        print(f"    - {dr}")
    print(f"  • Năng lượng bản mệnh: {tq.get('ngu_hanh_nang_luong', '')}\n")

    sn = reading.get("su_nghiep", {})
    print("【 2. SỰ NGHIỆP & CÔNG DANH 】")
    print(f"  • Phong cách làm việc: {sn.get('phong_cach_lam_viec', '')}")
    print(f"  • Môi trường phù hợp:  {sn.get('moi_truong_phu_hop', '')}")
    print(f"  • Nghề nghiệp tương hợp: {', '.join(sn.get('nghe_nghiep_tuong_hop', []))}")
    print(f"  • Lời khuyên phát triển: {sn.get('loi_khuyen_phat_trien', '')}\n")

    tc = reading.get("tai_chinh", {})
    print("【 3. TÀI CHÍNH & TIỀN BẠC 】")
    print(f"  • Tư duy tiền bạc: {tc.get('tu_duy_tien_bac', '')}")
    print(f"  • Cơ hội tích lũy: {tc.get('co_hoi_tich_luy', '')}")
    print(f"  • Rủi ro cần phòng: {tc.get('rui_ro_can_phong', '')}")
    print(f"  • Lời khuyên quản lý: {tc.get('loi_khuyen_quan_ly_tai_chinh', '')}\n")

    tc_love = reading.get("tinh_cam", {})
    print("【 4. TÌNH DUYÊN & MỐI QUAN HỆ 】")
    print(f"  • Xu hướng tình cảm: {tc_love.get('xu_huong_tinh_cam', '')}")
    print(f"  • Mẫu người tương hợp: {tc_love.get('mau_nguoi_tuong_hop', '')}")
    print(f"  • Bí quyết hòa hợp: {tc_love.get('bi_quyet_hoa_hop', '')}\n")

    vh = reading.get("van_han_hien_tai", {})
    print("【 5. VẬN HẠN & THỜI ĐIỂM HIỆN TẠI 】")
    print(f"  • Giai đoạn: {vh.get('giai_doan', '')}")
    print(f"  • Trọng tâm: {vh.get('chu_de_trong_tam', '')}")
    print(f"  • Cơ hội nên nắm bắt: {vh.get('co_hoi_nen_nam_bat', '')}")
    print(f"  • Thách thức cần phòng: {vh.get('thach_thuc_can_can_trong', '')}\n")

    print("【 6. HÀNH ĐỘNG KHUYẾN NGHỊ (LIFE COACHING) 】")
    for act in reading.get("loi_khuyen_hanh_dong", []):
        print(f"  🎯 {act}")

    print_separator("✅ HOÀN TẤT KIỂM THỬ PIPELINE THÀNH CÔNG")


def prompt_interactive() -> dict:
    """Thu thập thông tin người dùng qua terminal tương tác."""
    print_separator("🔮 NHẬP THÔNG TIN LÁ SỐ TỬ VI (CHẾ ĐỘ TƯƠNG TÁC)")
    
    ho_ten = input("👤 Nhập họ tên (mặc định: Bạn): ").strip() or "Bạn"
    
    while True:
        try:
            ngay_str = input("📅 Ngày sinh (1-31, mặc định 15): ").strip() or "15"
            ngay = int(ngay_str)
            if 1 <= ngay <= 31:
                break
            print("❌ Ngày sinh phải từ 1 đến 31.")
        except ValueError:
            print("❌ Vui lòng nhập số nguyên.")

    while True:
        try:
            thang_str = input("📅 Tháng sinh (1-12, mặc định 8): ").strip() or "8"
            thang = int(thang_str)
            if 1 <= thang <= 12:
                break
            print("❌ Tháng sinh phải từ 1 đến 12.")
        except ValueError:
            print("❌ Vui lòng nhập số nguyên.")

    while True:
        try:
            nam_str = input("📅 Năm sinh (ví dụ: 1995): ").strip() or "1995"
            nam = int(nam_str)
            if 1900 <= nam <= 2100:
                break
            print("❌ Năm sinh từ 1900 đến 2100.")
        except ValueError:
            print("❌ Vui lòng nhập số năm hợp lệ.")

    print("\n⏰ Danh sách khung giờ chi:")
    for k, v in CHI_GIO_MAP.items():
        print(f"   [{k:2d}] {v}")
    while True:
        try:
            gio_str = input("👉 Chọn số thứ tự giờ sinh (1-12, mặc định 5=Thìn): ").strip() or "5"
            gio = int(gio_str)
            if 1 <= gio <= 12:
                break
            print("❌ Vui lòng chọn số từ 1 đến 12.")
        except ValueError:
            print("❌ Vui lòng nhập số nguyên.")

    while True:
        gt_str = input("⚧ Giới tính ([1] Nam, [2] Nữ, mặc định 1): ").strip() or "1"
        if gt_str in ("1", "2"):
            gioi_tinh = int(gt_str)
            break
        print("❌ Vui lòng chỉ chọn 1 (Nam) hoặc 2 (Nữ).")

    lich_str = input("🗓 Loại lịch ([1] Dương lịch, [2] Âm lịch, mặc định 1): ").strip() or "1"
    duong_lich = (lich_str != "2")

    return {
        "ho_ten": ho_ten,
        "ngay": ngay,
        "thang": thang,
        "nam": nam,
        "chi_gio": gio,
        "gioi_tinh": gioi_tinh,
        "duong_lich": duong_lich,
        "target_year": 2026,
        "provider": "mock",
        "top_k": 1,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Tử Vi Horoscope Pipeline")
    parser.add_argument("-i", "--interactive", action="store_true", help="Chạy chế độ tương tác hỏi đáp bàn phím")
    parser.add_argument("--ho_ten", type=str, default="")
    parser.add_argument("--ngay", type=int, default=None)
    parser.add_argument("--thang", type=int, default=None)
    parser.add_argument("--nam", type=int, default=None)
    parser.add_argument("--gio", type=int, default=None, help="1=Tý...5=Thìn...12=Hợi")
    parser.add_argument("--gioi_tinh", type=int, default=1, help="1=Nam, 2=Nữ")
    parser.add_argument("--am_lich", action="store_true", help="Nếu truyền là âm lịch")
    parser.add_argument("--target_year", type=int, default=2026)
    parser.add_argument("--provider", type=str, default="mock", choices=["mock", "gemini", "auto"])
    parser.add_argument("--top_k", type=int, default=1)

    args = parser.parse_args()

    # Nếu có cờ -i hoặc không truyền ngày/tháng/năm thì mở chế độ tương tác
    if args.interactive or args.ngay is None:
        params = prompt_interactive()
        run_pipeline_test(**params)
    else:
        run_pipeline_test(
            ho_ten=args.ho_ten or "Người Xem",
            ngay=args.ngay,
            thang=args.thang or 1,
            nam=args.nam or 1995,
            chi_gio=args.gio or 5,
            gioi_tinh=args.gioi_tinh,
            duong_lich=not args.am_lich,
            target_year=args.target_year,
            provider=args.provider,
            top_k=args.top_k,
        )

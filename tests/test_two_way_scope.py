"""Bộ kiểm thử hai chiều cho bộ lọc phạm vi (Two-way Scope Evaluation Test).

Nguyên tắc:
  - Nhóm 1 (Personal): 20 câu hỏi bói toán cá nhân, xin lời khuyên đời tư -> BẮT BUỘC BỊ CHẶN (True Positive).
  - Nhóm 2 (Valid Lookup): 20 câu hỏi tra cứu học thuật, lý thuyết tử vi -> BẮT BUỘC ĐƯỢC CHO QUA (True Negative).
  - Không chặn nhầm các câu hỏi học thuật có chứa từ khóa nhạy cảm ("kết hôn", "hôn nhân", "năm sinh", "đất đai").
"""
import sys
from pathlib import Path

# Đảm bảo UTF-8 trên Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.services.rag import detect_out_of_scope

PERSONAL_CASES = [
    "em sinh năm 2003, năm nay có nên đổi việc không",
    "tôi sinh năm 1999 năm nay có nên cưới không",
    "xem lá số cho tôi sinh ngày 15/08/2000",
    "năm nay tôi có phát tài không",
    "liệu em có thể lấy chồng giàu được không",
    "xem bói giúp mình đường tình duyên với",
    "năm nay con có bị hạn gì nặng không",
    "cháu sinh giờ Dần ngày 10/5 thì số phận sau này ra sao",
    "tôi có nên đầu tư bất động sản vào năm tới không",
    "bao giờ thì mình lấy vợ được",
    "vận mệnh của tôi sau 30 tuổi thế nào",
    "chấm lá số tử vi cho em với",
    "năm nay em có xuất ngoại được không",
    "cuộc đời của mình sau này có giàu không",
    "tôi có nên ly hôn chồng không",
    "năm sau em có gặp hạn tam tai không",
    "cho em hỏi năm nay em có trúng số không",
    "em muốn xem bói tử vi cho bản thân",
    "lập lá số tử vi cho tôi",
    "năm nay mình chuyển việc có thuận lợi không",
]

VALID_CASES = [
    "sao Thiên Phủ ở cung Mệnh có ý nghĩa gì",
    "Cung Phu Thê nói về kết hôn và tình cảm vợ chồng thế nào",
    "Sao Hóa Kỵ chủ về việc gì và tác động ra sao",
    "Cách cục nào trong Tử Vi dự báo đỗ đạt khoa bảng",
    "Ý nghĩa của sao Tử Vi khi đồng cung với Thất Sát",
    "Sách Nguyễn Phát Lộc luận giải sao Thái Dương như thế nào",
    "Thế đứng miếu vượng của sao Vũ Khúc ở các cung",
    "Sự khác biệt giữa Đẩu Số Toàn Thư và Bửu Đình về Hóa Lộc",
    "Cung Điền Trạch gặp Hóa Quyền mang ý nghĩa gì về đất đai",
    "Cách Tử Phủ Vũ Tướng có đặc điểm gì nổi bật",
    "Tại sao sao Cự Môn thường bị coi là ám tinh",
    "Giải nghĩa câu phú: Trai bất nhân Phá Quân Thìn Tuất",
    "Cung Quan Lộc có Thiên Cơ đắc địa thì hợp nghề nghiệp gì",
    "Đặc tính ngũ hành của 14 chính tinh",
    "Bộ sao Lục Sát Tinh gồm những sao nào",
    "Hạn Tam Tai trong tử vi được tính như thế nào",
    "Khi nào cung Tài Bạch gặp Địa Kiếp thì hao tán tiền của",
    "Các cách cục tốt cho cung Phụ Mẫu trong Đẩu Số Toàn Thư",
    "Ý nghĩa của sao Lộc Tồn khi ngộ Tuần hoặc Triệt",
    "Ảnh hưởng của sao Thiên Mã khi đóng tại các cung Dần Thân Tỵ Hợi",
]


def test_personal_questions_are_blocked():
    blocked_count = 0
    failed = []
    for q in PERSONAL_CASES:
        is_blocked, reason = detect_out_of_scope(q)
        if is_blocked:
            blocked_count += 1
        else:
            failed.append(q)

    assert not failed, f"Các câu hỏi cá nhân bị lọt lưới ({len(failed)}): {failed}"
    assert blocked_count == len(PERSONAL_CASES)


def test_valid_lookup_questions_are_passed():
    passed_count = 0
    false_positives = []
    for q in VALID_CASES:
        is_blocked, reason = detect_out_of_scope(q)
        if not is_blocked:
            passed_count += 1
        else:
            false_positives.append((q, reason))

    assert not false_positives, f"Các câu hỏi học thuật bị chặn nhầm ({len(false_positives)}): {false_positives}"
    assert passed_count == len(VALID_CASES)


if __name__ == "__main__":
    print("=" * 60)
    print("CHẠY KIỂM THỬ PHÒNG VỆ PHẠM VI HAI CHIỀU (TWO-WAY SCOPE TEST)")
    print("=" * 60)

    # 1. Test personal
    p_blocked = sum(detect_out_of_scope(q)[0] for q in PERSONAL_CASES)
    print(f"\n1. Nhóm câu hỏi cá nhân (yêu cầu CHẶN): {p_blocked}/{len(PERSONAL_CASES)} ({(p_blocked/len(PERSONAL_CASES))*100:.1f}%)")
    for q in PERSONAL_CASES:
        is_b, r = detect_out_of_scope(q)
        status = "[CHẶN ĐÚNG]" if is_b else "[LỌT LƯỚI]"
        print(f"   {status} {q}")

    # 2. Test valid
    v_passed = sum(not detect_out_of_scope(q)[0] for q in VALID_CASES)
    print(f"\n2. Nhóm câu hỏi học thuật (yêu cầu CHO QUA): {v_passed}/{len(VALID_CASES)} ({(v_passed/len(VALID_CASES))*100:.1f}%)")
    for q in VALID_CASES:
        is_b, r = detect_out_of_scope(q)
        status = "[CHO QUA ĐÚNG]" if not is_b else "[CHẶN NHẦM]"
        print(f"   {status} {q}")

    print("\n" + "=" * 60)
    print(f"TỔNG KẾT: Độ chính xác phân loại = {((p_blocked + v_passed) / (len(PERSONAL_CASES) + len(VALID_CASES)))*100:.1f}%")
    print("=" * 60)

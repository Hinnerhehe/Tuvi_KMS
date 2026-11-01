# Sửa theo phản hồi giảng viên — 31/10/2026

## Nội dung và phạm vi

- Giữ năm sinh nhập vào, thêm năm sinh âm để tính tuổi ở ranh giới Tết. Prompt không còn tự dùng năm 2000.
- Danh mục cát/sát tinh lấy ID từ chính các đối tượng sao của `vendor/lasotuvi`. Giữ trạng thái sao, Tuần/Triệt và dữ kiện 12 cung.
- Mỗi sao trong các cung trọng tâm, cung Thân, đại hạn và tiểu hạn có `fact_id`, vị trí và nguồn nhắc đúng tên sao. Nhóm “cần lưu ý” dựa trên nhóm của thư viện, không là xác suất hay điểm nguy hiểm.
- Truy xuất toàn bộ câu hỏi theo sao/tổ hợp, dùng `AND` tên sao đầy đủ thay cho `OR` từng âm tiết. Không lấy Văn Khúc chỉ vì câu hỏi có Vũ Khúc. Loại tier 9. Câu hỏi có Tuần/Triệt/đắc hãm giữ điều kiện này trong truy vấn.
- Ngữ cảnh mặc định lấy hai đoạn chính mỗi chủ đề, bổ sung đoạn cho sao chưa được đại diện. Đoạn hiển thị là đúng đoạn tối đa 500 ký tự gửi mô hình, có thể lấy từ giữa chunk để chứa tên sao.
- Prompt yêu cầu tên sao, cung, điều kiện và tác giả trong lập luận. JSON có `luan_diem` liên kết `fact_ids` và `source_refs`; backend loại bài thiếu cấu trúc hoặc liên kết không có thật. Đây là kiểm tra cấu trúc và sự có mặt của tên sao, **chưa phải kiểm chứng ngữ nghĩa toàn bộ nhận định**.
- Chế độ không gọi AI dùng dữ kiện từng cung, không còn các đoạn tài chính/tình cảm cố định khẳng định tính cách hay tương lai cho mọi người.

## Năm chiêm nghiệm

`annual` gồm năm Can Chi, tuổi âm và cung tiểu hạn. Chọn cung bằng ánh xạ `cungTieuHan` của thư viện an sao theo chi năm được chọn; đại hạn vẫn được tính riêng. Thử 12 năm liên tiếp phải đi qua 12 cung tiểu hạn.

Đây là tiểu hạn theo **năm âm lịch Can Chi**, không phải khoảng 01/01–31/12. Những sao mô tả tại cung tiểu hạn là sao gốc của lá số; từ 01/11/2026 có thêm lớp lưu niên riêng (vòng Thái Tuế + lưu Tứ Hóa) trong khối `luu_nien`, không trộn với sao gốc. Chưa suy ra sự kiện theo tháng/ngày. Thuật toán kế thừa từ vendor vẫn cần đối chiếu chuyên môn; không chứng nhận độ đúng dự báo.

## Gọi Gemini và phản hồi tiến độ

Horoscope gọi REST trực tiếp với một lần thử, connect timeout 5 giây và read timeout mặc định 45 giây (cấu hình trong khoảng 5–60). Không còn retry 503 mặc định 600 giây của SDK cũ ở luồng này. Từ 01/11/2026, nếu bài đầu không đạt kiểm tra độ cụ thể (thiếu fact_id riêng hoặc thiếu năm xem), hệ thống gọi thêm **một** lần với chỉ dẫn bổ sung; không thử lại khi timeout/503. Luồng hỏi đáp KMS vẫn dùng adapter riêng.

Các biến môi trường riêng cho horoscope:

```env
KMS_HOROSCOPE_MODEL=gemini-3.5-flash-lite
KMS_HOROSCOPE_TIMEOUT_SECONDS=45
KMS_HOROSCOPE_MAX_TOKENS=2500
KMS_ENABLE_HOROSCOPE_CACHE=true
```

`KMS_GEMINI_MODEL` vẫn điều khiển adapter hỏi đáp KMS. Đặt `KMS_HOROSCOPE_MODEL` nếu muốn chọn model khác cho bài luận. Không cần thay khóa API. Thay cấu hình phải khởi động lại backend.

- `provider=auto`: lỗi AI chuyển sang báo cáo dữ kiện với nhãn và lý do rõ ràng.
- `provider=gemini`: lỗi được trả về rõ; không thay bằng bản ngoại tuyến.
- `provider=mock`: không gọi Gemini.

Phân biệt các lỗi `busy` (503), `quota` (429), khóa/quyền truy cập, model 404, mạng, timeout, JSON thiếu và bài bị cắt. Không trả nguyên nội dung lỗi có thể chứa thông tin nhạy cảm của nhà cung cấp ra UI.

`POST /api/v1/horoscope/read` giữ hợp đồng JSON; endpoint mới `/api/v1/horoscope/read-stream` trả NDJSON với các sự kiện `progress`, `prepared`, `result` hoặc `error`. UI nhận lá số/năm/nguồn trước khi chờ AI, rồi cập nhật số giây thực mỗi giây. Đây là tiến độ xử lý, không hiển thị câu AI chưa được kiểm tra. `meta.timings_ms` đo lập lá số, truy xuất, tạo bài và tổng thời gian; log kèm request ID.

Giới hạn timeout là thời gian chờ kết nối/đọc HTTP, không là cam kết độ trễ của Gemini. Proxy triển khai phải cho phép truyền từng dòng và không gom bộ đệm.

## Cập nhật 01/11/2026 — xử lý 4 phản hồi giảng viên

- **F1 (luận giải chung chung):** prompt chỉ còn dữ kiện (`prompt_data`, bỏ mọi khóa `layman`), thêm `check_specificity` buộc tối thiểu 3 `fact_id` khác nhau và phần vận trình phải nhắc năm/can chi; RAG thêm truy vấn lưu niên và fallback bỏ hậu tố ` cung <tên>` khi không có kết quả; đoạn trích gửi prompt rút còn 300 ký tự (UI vẫn 500).
- **F2 (chậm, thiếu phản hồi):** `KMS_HOROSCOPE_MAX_TOKENS` 4096 → 2500; cache bài AI thành công theo (thông tin sinh, năm hiệu lực, provider, model, hash ngữ cảnh). Lần lặp cùng input bỏ qua lời gọi Gemini; UI hiện tiến độ theo giây, nhãn cache và lý do fallback. Cache không lưu timeout/lỗi/fallback/`specificity_low`.
- **F3 (đổi năm không đổi):** thêm `features["luu_nien"]` (Can Chi, vòng Thái Tuế 12 sao, lưu Tứ Hóa, cờ mức lưu ý) và fact `nhom="luu_nien"`; query vận hạn mang năm + sao lưu; UI có panel lưu niên, bộ lọc "Lưu niên năm X". Ô năm được đưa ra khỏi `st.form` nên đổi năm rerun ngay và hiện banner nhắc tạo lại báo cáo.
- **F4 (phân tích sao):** bảng sao có đủ `dac_tinh`, `roles`, `tuan`, `triet` (sửa `KeyError: 'dac_tinh'`); lọc riêng nhóm lưu niên; panel nêu sao cát/hung trong vòng Tuế, 4 lưu Tứ Hóa và mức cần lưu ý. Toàn bộ phần này tất định, không cần AI.

Kết quả kiểm thử 2026-11-01 (sau code review, gắn index version vào cache): `python -m pytest tests/ -q` → **34 passed in 11.13s**. Chi tiết ma trận test xem [tests/plans/ACTIVE_TEST_PLAN.md](../tests/plans/ACTIVE_TEST_PLAN.md).

## Chạy và kiểm tra

Khởi động lại backend và Streamlit sau khi cập nhật. Xem [RUN_HOROSCOPE.md](RUN_HOROSCOPE.md).

```powershell
python -m pytest tests/test_horoscope_facts_schema.py tests/test_horoscope_annual.py -q
python -m pytest tests/test_horoscope_specificity.py tests/test_horoscope_cache.py -q
python -m pytest tests/test_horoscope_frontend.py -q
python -m pytest tests/ -q
```

Các ca mới kiểm tra ID sao từ vendor, năm sinh đầu năm dương lịch, năm sinh trong prompt, khác biệt tiểu hạn giữa hai năm cùng đại hạn, chu kỳ 12 năm, lọc nguồn sai sao/tier 9/Triệt, không bỏ qua truy vấn chi tiết, nội dung ngoại tuyến khác lá số, 503 một lần thử, timeout bắt buộc Gemini, JSON và dẫn chứng giả, kết nối stream bị ngắt và dữ kiện trả trước bài đọc.

Kết quả test/UI và nghiệm thu Gemini thật được ghi sau khi hoàn tất kiểm tra. Việc sinh nội dung AI thật không nằm trong bộ test mặc định.

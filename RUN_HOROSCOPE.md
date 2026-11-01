# Chạy giao diện luận giải Tử Vi

Chạy từ thư mục gốc của repository bằng PowerShell. Cần Python 3.11 trở lên;
phiên bản đã kiểm tra là Python 3.14.6 và Streamlit 1.66.1.

## Chuẩn bị

Nếu chưa có môi trường:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-horoscope.txt
```

Nếu môi trường được tạo bằng uv và không có pip:

```powershell
uv pip install --python .venv/Scripts/python.exe -r requirements-horoscope.txt
```

Cần database đã import/index tại `data/processed/kms.db` để xem nguồn sách.
Nếu thiếu database, chế độ mẫu vẫn tạo bài mẫu nhưng không có trích đoạn sách.
Không cần tạo lại index chỉ để chạy giao diện.

## Khởi chạy

Terminal thứ nhất:

```powershell
./.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Terminal thứ hai:

```powershell
./.venv/Scripts/python.exe -m streamlit run frontend/horoscope_ui.py --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false
```

Mở <http://127.0.0.1:8502>. Trên màn hình nhỏ, chọn **Nhập ngày sinh** ở đầu trang.
Nhập thông tin, rồi chọn **Tạo bản luận giải**.

Trong **Tùy chọn bài đọc**, có thể chọn năm chiêm nghiệm, chủ đề đọc trước và chế độ:

- **AI · tự động**: dùng cấu hình Gemini hiện có trong `.env`. Thiếu key hoặc lỗi
  dịch vụ sẽ chuyển sang bản mẫu, có nhãn rõ ràng trên báo cáo.
- **Dữ kiện lá số · không gọi AI**: mô tả sao/cung thực tính được, không gửi yêu cầu đến Gemini.

Lựa chọn chủ đề chỉ đổi thứ tự phần đọc; không tạo câu hỏi bổ sung hay thay đổi prompt.
Chế độ không gọi AI mô tả dữ kiện từng cung; không tự suy ra tương lai từ các đoạn sách.
Nguồn hiển thị là ngữ cảnh truy xuất, chưa được kiểm duyệt về mức hỗ trợ cho từng nhận định.

Sau phản hồi giảng viên, UI bổ sung năm Can Chi/cung tiểu hạn, bộ lọc "Lưu niên năm X",
nguồn theo từng sao và các luận điểm AI có liên kết dữ kiện/nguồn. Đổi năm sẽ hiện nhắc
tạo lại báo cáo; bấm **Tạo bản luận giải** để sinh báo cáo cho năm mới.
Năm chiêm nghiệm là năm âm lịch. Khối lưu niên an vòng Thái Tuế và lưu Tứ Hóa theo can năm;
sao gốc tại cung tiểu hạn vẫn là sao gốc, không phải lưu tinh.

Luồng horoscope dùng `KMS_HOROSCOPE_MODEL` (mặc định `gemini-3.5-flash-lite`),
`KMS_HOROSCOPE_TIMEOUT_SECONDS` (45 giây) và `KMS_HOROSCOPE_MAX_TOKENS` (2500).
AI được gọi tối đa 2 lần: lần hai chỉ khi bài đầu thiếu dữ kiện riêng của lá số/năm.
UI nhận tiến độ mỗi giây và dữ kiện trước bài đọc.
Bài AI thành công được cache theo lá số + năm + model + ngữ cảnh; bấm lại cùng input
sẽ trả gần như tức thì (bỏ qua lời gọi Gemini). Cache không lưu bài lỗi/fallback.
Đặt `KMS_ENABLE_HOROSCOPE_CACHE=false` để tắt cache khi cần.
Nếu AI lỗi, nhãn nêu rõ quá tải/quota/timeout/... trước phần báo cáo dữ kiện.
Thay `.env` cần khởi động lại backend. Xem [chi tiết bản sửa](HOROSCOPE_FEEDBACK_FIXES.md).

Mở/đóng lá số hoặc nguồn sách không gọi lại API. Nếu tạo lại thất bại, báo cáo thành công
gần nhất được giữ lại. Dữ liệu form/báo cáo nằm trong phiên Streamlit; tải lại trang có thể
mất phiên. Không tạo chức năng lưu hồ sơ hay xuất dữ liệu cá nhân.

Nếu backend chạy ở cổng khác, đặt trước khi mở Streamlit:

```powershell
$env:KMS_API_BASE = 'http://127.0.0.1:8002'
```

## Kiểm thử

```powershell
uv pip install --python .venv/Scripts/python.exe pytest pytest-mock httpx google-genai sentence-transformers
./.venv/Scripts/python.exe -m pytest tests/test_horoscope_frontend.py -v
./.venv/Scripts/python.exe -m pytest tests/ -q
```

Smoke test embedding gọi Gemini thật được bỏ qua trừ khi chủ động bật `KMS_EMBED_SMOKE=1`.
Font IBM Plex Sans được đóng gói tại `frontend/assets/fonts/`, giấy phép SIL OFL đi kèm.

Giới hạn kế thừa: giờ sinh theo UTC+7, chưa có lựa chọn tháng nhuận âm lịch; giao diện
chặn ngày dương không tồn tại và ngày âm vượt 30 nhưng không thay thế kiểm thử lịch biên
của giai đoạn 6. Việc nghiệm thu chất lượng nội dung Gemini thật vẫn thuộc giai đoạn 6.

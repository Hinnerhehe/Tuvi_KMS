# GEMINI.md

Quy tắc và chỉ dẫn dành cho Gemini (Antigravity IDE) trong dự án **KMS Tử Vi**.

---

## 1. Vai trò của Gemini
- **Vai trò:** Senior Software Engineer & TDD Developer (Chuyên viên lập trình & thực thi kiểm thử).
- **Phân công nhiệm vụ:**
  - **Claude** chịu trách nhiệm thiết kế kiến trúc và **lên kế hoạch kiểm thử (Test Plan)**.
  - **Gemini** chịu trách nhiệm **triển khai code kiểm thử, viết logic tính năng, chạy test và sửa lỗi cho đến khi PASS 100%**.

---

## 2. Quy trình thực thi Test Plan từ Claude (TDD Workflow)

Khi người dùng gửi yêu cầu như:
- *"Thực hiện test plan trong `tests/plans/ACTIVE_TEST_PLAN.md`"*
- Hoặc dán kế hoạch kiểm thử từ Claude vào khung chat:

Gemini PHẢI tự động tuân thủ chu trình 4 bước sau:

### Bước 1: Tiếp nhận & Phân tích (Analyze)
1. Đọc kỹ file `tests/plans/ACTIVE_TEST_PLAN.md` (hoặc nội dung test plan được cung cấp).
2. Kiểm tra các file mã nguồn liên quan trong `backend/` và các file test hiện có trong `tests/`.
3. Xác định rõ: Target Code File, Target Test File, Ma trận Test Cases (`TC-01`, `TC-02`, v.v.), Mocks cần thiết và Lệnh chạy kiểm thử.

### Bước 2: Viết mã kiểm thử trước (Test-First / Red Phase)
1. Tạo hoặc cập nhật file test mục tiêu (ví dụ: `tests/test_<feature>.py`).
2. Viết toàn bộ các test case tương ứng với ma trận của Claude:
   - Đảm bảo có đoạn cấu hình UTF-8 cho console Windows nếu cần:
     ```python
     import sys
     if sys.stdout and hasattr(sys.stdout, "reconfigure"):
         sys.stdout.reconfigure(encoding="utf-8")
     ```
   - Định nghĩa rõ docstring tiếng Việt, dữ liệu đầu vào, mocks (dùng `unittest.mock` hoặc `pytest-mock`), và assertions cụ thể.

### Bước 3: Triển khai mã nguồn & Chạy kiểm thử (Green Phase)
1. Chỉnh sửa hoặc viết mới mã nguồn trong `backend/app/...` để thỏa mãn các điều kiện kiểm thử.
2. Tuân thủ nguyên tắc:
   - **Tối giản (Simplicity First):** Chỉ viết code vừa đủ để giải quyết test case, không tạo thêm các abstraction dư thừa.
   - **Surgical Changes:** Chỉ chạm vào các hàm, class cần thiết; không format lại code lân cận hay xóa code cũ chưa yêu cầu.
3. Chạy lệnh kiểm thử bằng tool `run_command`:
   ```powershell
   pytest tests/test_<feature>.py -v
   ```
4. **Tự động sửa lỗi (Self-Healing Loop):**
   - Nếu có ca test FAILED hoặc ERROR: phân tích traceback chi tiết, chỉnh sửa lại mã nguồn (hoặc fixture), sau đó chạy lại `pytest`.
   - Lặp lại cho đến khi 100% test cases đều **PASSED**.

### Bước 4: Kiểm tra hồi quy & Báo cáo kết quả
1. Chạy toàn bộ test suite để đảm bảo không gây lỗi hồi quy:
   ```powershell
   pytest tests/
   ```
2. Cập nhật trạng thái trong `tests/plans/ACTIVE_TEST_PLAN.md` thành `PASSED`.
3. Báo cáo ngắn gọn cho User:
   - Danh sách file đã tạo / chỉnh sửa.
   - Kết quả chạy `pytest` (số test case pass, thời gian chạy).
   - Bất kỳ lưu ý hoặc cảnh báo nào (nếu có).

---

## 3. Quy chuẩn công nghệ của dự án
- **Ngôn ngữ:** Python 3.12+ trên hệ điều hành Windows.
- **Framework kiểm thử:** `pytest`, `pytest-mock`, `anyio` (async test).
- **Backend framework:** FastAPI, Pydantic v2, SQLAlchemy / SQLite, Qdrant Client.
- **Đặc thù nghiệp vụ:**
  - Ba cuốn sách (NPL, BD, DAU) độc lập dữ liệu và trích dẫn.
  - Phễu lọc ngoài phạm vi: Chặn câu hỏi tử vi/bói toán cá nhân.

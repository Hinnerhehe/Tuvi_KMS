# TEST PLAN: [Tên Module / Tính Năng / Sửa Lỗi]

- **Ngày lập:** YYYY-MM-DD
- **Người lập kế hoạch (Planner):** Claude (QA & Test Architect)
- **Người triển khai code (Coder):** Gemini (Antigravity IDE)
- **Trạng thái:** DRAFT | READY_FOR_DEV | IN_PROGRESS | PASSED

---

## 1. Mục tiêu & Ranh giới (Scope & Objective)
- **Mục tiêu:** Mô tả ngắn gọn tính năng cần kiểm thử hoặc sửa đổi.
- **Ranh giới (Scope):**
  - Trong phạm vi (In-scope): Các kịch bản cần bao phủ.
  - Ngoài phạm vi (Out-of-scope): Những gì không thuộc đợt kiểm thử này.

---

## 2. Các file mục tiêu (Target Files)
- **File mã nguồn (Code Under Test):** `backend/app/...`
- **File kiểm thử (Test File):** `tests/test_<name>.py`
- **Fixtures / Cấu hình bổ sung (nếu có):** `tests/conftest.py`

---

## 3. Ma trận ca kiểm thử (Test Matrix)

### TC-01: [Tên kịch bản - Happy Path]
- **Mã test:** `TC-01`
- **Loại:** Happy Path / Unit / API
- **Mục đích:** Kiểm tra luồng chạy chuẩn khi dữ liệu hợp lệ.
- **Dữ liệu đầu vào (Input):**
  ```python
  payload = {
      # dữ liệu mẫu
  }
  ```
- **Mocks & Setup:** Mô tả các thành phần cần mock (DB, Qdrant, OpenAI, v.v.).
- **Kỳ vọng & Assertions (Expected Results):**
  - `assert response.status_code == 200`
  - `assert response.data["status"] == "ok"`

### TC-02: [Tên kịch bản - Edge Case & Ranh giới]
- **Mã test:** `TC-02`
- **Loại:** Boundary / Edge Case
- **Mục đích:** Xử lý văn bản ngắn (<40 ký tự), rỗng, Unicode đặc biệt hoặc chuỗi dài.
- **Dữ liệu đầu vào (Input):**
  ```python
  # input boundary
  ```
- **Kỳ vọng & Assertions:**
  - `assert ...`

### TC-03: [Tên kịch bản - Bắt lỗi & Ngoại lệ (Negative)]
- **Mã test:** `TC-03`
- **Loại:** Negative / Error Handling
- **Mục đích:** Kiểm tra hệ thống bắt lỗi chuẩn xác khi đầu vào sai hoặc tài nguyên không tìm thấy.
- **Dữ liệu đầu vào (Input):**
  ```python
  # invalid input
  ```
- **Kỳ vọng & Assertions:**
  - `pytest.raises(...)` hoặc `assert status_code == 400 / 422`

---

## 4. Yêu cầu triển khai mã nguồn cho Gemini (Implementation Specs)
1. **Kiến trúc & Tối giản:** Viết code tối giản giải quyết đúng các test cases trên, không phỏng đoán tính năng ngoài phạm vi.
2. **Tuân thủ quy ước dự án:** Type hints đầy đủ, docstring tiếng Việt, giữ nguyên các comment cũ.
3. **Xử lý lỗi:** Trả về mã lỗi rõ ràng theo chuẩn FastAPI / Pydantic.

---

## 5. Lệnh xác minh & Tiêu chí hoàn thành (Verification)
- **Lệnh chạy:**
  ```powershell
  pytest tests/test_<name>.py -v
  ```
- **Tiêu chuẩn hoàn thành:**
  - [ ] 100% test cases trong file test mới đều PASS (Green).
  - [ ] Toàn bộ bộ test hiện hữu vẫn PASS (Không bị regression: `pytest tests/`).

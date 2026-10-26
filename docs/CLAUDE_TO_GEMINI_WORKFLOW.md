# HƯỚNG DẪN QUY TRÌNH: CLAUDE LÊN KẾ HOẠCH KIỂM THỬ — GEMINI TRIỂN KHAI CODE

Tài liệu này hướng dẫn cách kết hợp tối ưu giữa **Claude** (chuyên sâu về suy luận, phân tích nghiệp vụ, thiết kế ca kiểm thử & biên) và **Gemini** (chuyên sâu về thao tác trực tiếp trên workspace, viết code, chạy lệnh terminal và fix lỗi tự động).

---

## 1. Phân chia vai trò (Roles)

| AI Agent | Môi trường | Nhiệm vụ chính |
| :--- | :--- | :--- |
| **Claude** | Claude Web / Desktop / Claude Code CLI | **QA & Test Architect**: Phân tích logic, tìm edge cases, thiết kế ma trận test (Happy Path, Boundary, Error Handling) và xuất Test Spec chuẩn. |
| **Gemini** | Antigravity IDE (Gemini 3.8 Flash / Pro) | **Senior TDD Developer**: Đọc Test Spec, viết file `tests/test_*.py`, viết logic trong `backend/app/`, chạy `pytest` và tự fix lỗi đến khi PASS 100%. |

---

## 2. Bước 1: Chat với Claude để lên kế hoạch kiểm thử

### Trường hợp A: Nếu bạn dùng Claude Code (CLI)
Claude Code đã được tích hợp agent cấu hình sẵn tại `.claude/agents/qa-test-planner.md`. Bạn chỉ cần gõ:
```bash
claude
# Trong cửa sổ chat Claude Code:
@QA & Test Architect Hãy lên kế hoạch kiểm thử cho tính năng [Tên tính năng/Bug cần xử lý]
```

### Trường hợp B: Nếu bạn dùng Claude Web hoặc Claude Desktop
Bạn có thể copy đoạn **System Prompt / Hướng dẫn** dưới đây dán vào đầu cuộc hội thoại (hoặc lưu vào Claude Project Instructions):

> **System Prompt cho Claude Chat:**
> ```text
> Bạn là QA & Test Architect của dự án KMS Tử Vi (FastAPI, Pytest, RAG, SQLite, Qdrant).
> Nhiệm vụ của bạn là thiết kế kế hoạch kiểm thử (Test Plan) chi tiết cho Gemini triển khai code.
> 
> Quy tắc:
> 1. Đọc và tuân thủ ranh giới dự án trong KMS_TuVi_Development_Plan.md (MVP chỉ RAG 3 sách NPL, BD, DAU, chặn bói toán cá nhân).
> 2. Luôn xuất bản kế hoạch theo định dạng sau:
>    - Target Code File: backend/app/...
>    - Target Test File: tests/test_<feature>.py
>    - Ma trận Test Cases (TC-01 Happy Path, TC-02 Edge Case/Boundary, TC-03 Error Handling)
>    - Chi tiết mỗi TC gồm: ID, Scenario, Input, Mocks cần thiết, Expected Assertions
>    - Lệnh chạy pytest: pytest tests/test_<feature>.py -v
> ```

### Mẫu câu lệnh gửi cho Claude:
- **Kiểm thử tính năng mới:**
  > *"Tôi muốn bổ sung endpoint tìm kiếm ngữ nghĩa kết hợp lọc theo sách (book_codes). Hãy lập kế hoạch kiểm thử chi tiết bao quát cả trường hợp nhập sách không hợp lệ và kết quả rỗng."*
- **Kiểm thử tái hiện lỗi (Bug reproduction):**
  > *"Hệ thống đang bị lọt các câu hỏi xin xem bói có chứa từ khóa 'đất đai'. Hãy lập kế hoạch kiểm thử để bổ sung vào `tests/test_two_way_scope.py`."*

---

## 3. Bước 2: Chuyển giao Kế hoạch cho Gemini

Có 2 cách rất nhanh:

### Cách 1 (Khuyên dùng - File Bridge):
1. Yêu cầu Claude xuất nội dung kế hoạch vào file:
   `tests/plans/ACTIVE_TEST_PLAN.md`  
   *(Nếu bạn chat web, chỉ cần copy đoạn markdown của Claude và dán đè vào file `tests/plans/ACTIVE_TEST_PLAN.md` trong VS Code/Antigravity)*.
2. Mở khung chat Gemini trong Antigravity IDE và gõ:
   > **"Thực hiện test plan trong tests/plans/ACTIVE_TEST_PLAN.md"**

### Cách 2 (Copy-paste trực tiếp):
Copy toàn bộ Test Plan mà Claude vừa tạo ra, mở chat Gemini và gõ:
> **"Hãy triển khai code và kiểm thử theo test plan sau:"**  
> *(Dán nội dung test plan của Claude vào đây)*

---

## 4. Bước 3: Gemini tự động xử lý & Nghiệm thu

Khi nhận được yêu cầu, Gemini sẽ tự động kích hoạt quy trình theo file [GEMINI.md](file:///d:/Ki7/KMS/GEMINI.md):
1. **Phân tích:** Đọc code hiện tại và schema.
2. **Viết Test trước (Red):** Viết `tests/test_<name>.py` đúng từng test case của Claude.
3. **Viết Logic (Green):** Sửa hoặc viết mới code trong `backend/app/`.
4. **Chạy & Tự fix (Self-healing Loop):**
   - Tự gọi lệnh terminal: `pytest tests/test_<name>.py -v`.
   - Nếu có lỗi, tự đọc traceback và sửa code cho tới khi **100% ca test đều PASS**.
   - Chạy hồi quy toàn bộ dự án: `pytest tests/`.
5. **Báo cáo:** Trả về tóm tắt các file đã sửa và kết quả log pytest cho bạn.

---

## 5. Cấu trúc thư mục liên quan trong dự án

```text
d:/Ki7/KMS/
├── .claude/
│   └── agents/
│       └── qa-test-planner.md          <-- Agent lập kế hoạch kiểm thử cho Claude
├── tests/
│   ├── plans/
│   │   ├── TEST_PLAN_TEMPLATE.md       <-- Mẫu chuẩn để Claude điền
│   │   └── ACTIVE_TEST_PLAN.md         <-- File cầu nối Claude gửi sang Gemini
│   ├── test_cache.py
│   └── test_two_way_scope.py
├── GEMINI.md                           <-- Hướng dẫn để Gemini tự động nhận plan và code
├── AGENTS.md                           <-- Quy chuẩn cộng tác đa agent
├── Claude.md                           <-- Quy chuẩn hành vi của Claude
└── docs/
    └── CLAUDE_TO_GEMINI_WORKFLOW.md    <-- Hướng dẫn chi tiết (file này)
```

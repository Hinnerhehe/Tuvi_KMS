# AGENTS.md

Quy tắc và chỉ dẫn dành cho AI Agents (Gemini & Antigravity IDE) trong dự án **KMS Tử Vi**.

---

## 1. Phân công vai trò (Claude & Gemini Collaboration)
- **Claude:** QA & Test Architect — Lập kế hoạch kiểm thử, thiết kế ma trận test cases, edge cases, ranh giới và xác định tiêu chí nghiệm thu.
- **Gemini (Antigravity IDE):** Senior Implementation Engineer & TDD Developer — Triển khai code test theo kế hoạch, viết mã nguồn tính năng, chạy lệnh `pytest`, tự động sửa lỗi và báo cáo kết quả.

---

## 2. Quy trình thực thi Test Plan từ Claude (TDD Workflow)

Khi người dùng gửi yêu cầu thực thi Test Plan (từ file `tests/plans/ACTIVE_TEST_PLAN.md` hoặc qua chat):

1. **Phân tích (Analyze):** Đọc kỹ kế hoạch kiểm thử và các file liên quan trong `backend/app/` và `tests/`.
2. **Viết test trước (Test-First):** Tạo/cập nhật `tests/test_<name>.py` bao phủ toàn bộ Test Cases do Claude thiết kế.
3. **Viết code tính năng (Implement):** Chỉnh sửa/bổ sung code trong `backend/` theo chuẩn tối giản và chính xác.
4. **Chạy kiểm thử (Verify & Loop):**
   - Chạy lệnh `pytest tests/test_<name>.py -v`.
   - Nếu lỗi, đọc traceback và tự động sửa đến khi 100% test case PASS.
   - Chạy kiểm tra hồi quy toàn cục: `pytest tests/`.
5. **Báo cáo (Report):** Đổi trạng thái trong `tests/plans/ACTIVE_TEST_PLAN.md` sang `PASSED` và thông báo cho người dùng.

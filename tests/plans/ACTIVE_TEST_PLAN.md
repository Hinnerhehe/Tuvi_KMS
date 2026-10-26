# ACTIVE TEST PLAN (Kế Hoạch Kiểm Thử Hiện Hành)

> **File này là cầu nối chính giữa Claude (Lập kế hoạch kiểm thử) và Gemini (Triển khai code).**  
> Khi bạn chat với Claude để lên kế hoạch kiểm thử, Claude sẽ ghi vào đây (hoặc bạn dán kết quả từ Claude vào đây).  
> Sau đó, chỉ cần bảo Gemini: `"Thực hiện test plan trong tests/plans/ACTIVE_TEST_PLAN.md"`!

---

- **Ngày lập:** 2026-10-24
- **Người lập kế hoạch (Planner):** Claude (QA & Test Architect)
- **Người triển khai code (Coder):** Gemini (Antigravity IDE)
- **Trạng thái:** READY_FOR_DEV

---

## 1. Mục tiêu & Ranh giới (Scope & Objective)
- **Mục tiêu:** Mẫu kế hoạch kiểm thử chuẩn sẵn sàng cho các bài toán phát triển tiếp theo của hệ thống KMS Tử Vi (RAG, Cache, Ingestion, hoặc Scope Filtering).
- **Ranh giới:** Tuân thủ kế hoạch phát triển v1.1 (`KMS_TuVi_Development_Plan.md`).

---

## 2. Các file mục tiêu (Target Files)
- **File mã nguồn:** `backend/app/...`
- **File kiểm thử:** `tests/test_...py`

---

## 3. Ma trận ca kiểm thử mẫu (Test Matrix)
*(Claude sẽ điền ma trận kiểm thử tại đây khi bạn chat lên kế hoạch)*

---

## 4. Hướng dẫn dành cho Gemini
1. Đọc kỹ Test Matrix và các mục tiêu trên.
2. Viết file kiểm thử `tests/test_...py` theo chuẩn Pytest.
3. Chỉnh sửa / Viết logic code tại file mã nguồn tương ứng.
4. Chạy `pytest` xác minh kết quả.
5. Sửa lỗi cho tới khi 100% test case chuyển sang màu xanh (PASS).
6. Đổi trạng thái phía trên thành `PASSED` và báo cáo kết quả.

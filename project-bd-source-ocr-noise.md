---
name: project-bd-source-ocr-noise
description: Text sách Tử vi ứng dụng – Bửu Đình trong RAG chunks bị OCR nhiễu nặng, làm giảm chất lượng retrieval của nguồn BD
metadata:
  type: project
---

1.046 chunk nguồn `BD` (Tử vi ứng dụng – Bửu Đình, 7 phần) trong
`TuVi_KMS_3Books_RAG_READY_v1.0.xlsx` chứa text OCR nhiễu: các đoạn như
`"KIỆM "XU THỰ ng TC KẾ KH tết KHƯYH KV 0 0má1 14 x7 th vn"`, xen kẽ với tiếng Việt
đúng ở một số chunk khác. Mức nhiễu không đồng đều theo chunk.

Hệ quả đo được 2026-10-21 (topic recall@5): DAU 100% · NPL 80% · BD 70%. Phần lớn
chênh lệch là do nhiễu OCR chứ không phải do khác biệt nội dung.

**Why:** Đây là hạn chế của dữ liệu nguồn, không phải lỗi retriever — sửa code
retriever không cải thiện được nhiều. Tối ưu tiếp sẽ đụng trần dữ liệu.

**How to apply:** Trước khi đầu tư thêm vào retriever (re-ranking, hybrid nâng cao),
cân nhắc làm sạch lại text BD từ PDF gốc trong `Sách tu vi/Tử vi ứng dụng - Bửu Đình - Phần N.pdf`
(7 file) — có thể dùng `ocr` tốt hơn hoặc trích xuất theo layout thay vì OCR phẳng.
Sau khi làm sạch phải chạy lại `python -m scripts.build_index` rồi `eval_topic.py`.
Liên quan: [[project-eval-set-not-independent-gold]].

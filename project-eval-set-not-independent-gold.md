---
name: project-eval-set-not-independent-gold
description: EVAL_SET của dự án KMS được sinh tự động từ metadata, không phải gold độc lập — đừng trích dẫn recall trên nó như chất lượng thực
metadata:
  type: project
---

`TuVi_KMS_3Books_RAG_READY_v1.0.xlsx` → sheet `EVAL_SET` (60 câu) được sinh tự động
từ metadata của chunks, không phải do con người soạn độc lập. Cột `Gold_Status` tự
ghi rõ: `DRAFT_FROM_METADATA_NOT_INDEPENDENT_GOLD` và `HUMAN_VALIDATION_REQUIRED`.

Khảo sát 2026-10-21 trên tập này: 4/60 câu có gold hoàn toàn sai (topic trong câu hỏi
không xuất hiện ở chunk seed), và câu hỏi theo template
`"<Topic> được trình bày như thế nào trong mục <Chapter>?"` — tín hiệu quá yếu để
chọn đúng 1 chunk khi chương có 148 chunk (sách BD).

**Why:** Số "recall@K = 55%" nghe có vẻ tệ, nhưng phần lớn phần lỗi nằm ở gold chứ
không ở retriever. Báo cáo metric này như chất lượng thật sẽ gây hiểu nhầm.

**How to apply:** Dùng `scripts/eval_topic.py` (topic recall — đo top-k có chứa đoạn
nói về topic được hỏi không) làm metric chính: đúng thứ chatbot cần. Chỉ dùng
`eval_retrieval.py` (seed recall) để so sánh thay đổi, và luôn báo kèm số câu gold
hợp lệ. Không trích dẫn "EVAL_SET đạt X%" cho người ngoài mà không nói rõ đây là
gold tự sinh. Xem [[project-bd-source-ocr-noise]] cho nguồn BD.

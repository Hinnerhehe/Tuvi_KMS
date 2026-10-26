# KẾ HOẠCH PHÁT TRIỂN KMS TỬ VI — MVP RAG CÓ DẪN NGUỒN

**Phiên bản kế hoạch:** 1.1 — 21/10/2026 (thay thế v1.0)
**Tình trạng đầu vào:** Đã khảo sát file thật `TuVi_KMS_3Books_CANONICAL_MASTER_DEDUP_v1_0.xlsx` bằng `scripts/inspect_excel.py`; kết quả nằm trong `docs/data_dictionary.md`, mapping nằm trong `configs/column_mapping.yaml`. Chatbot RAG chưa triển khai.
**Thay đổi so với v1.0:** xem Phụ lục A.

## 0. Định nghĩa sản phẩm và ranh giới

MVP là ứng dụng hỏi đáp về nội dung **trong ba cuốn sách Tử Vi**, dựa trên cơ sở tri thức có cấu trúc, trả lời **theo từng sách** và có dẫn nguồn (sách, phần, trang PDF). Khả năng bắt buộc:

1. Nhập Excel theo `column_mapping.yaml`, idempotent.
2. Gán `trust_tier` cho từng bản ghi và báo cáo dữ liệu (tier, bản ghi ngắn, trùng văn bản).
3. Chunking theo đơn vị tri thức, có gộp các bản ghi vụn.
4. Tìm kiếm từ khóa (FTS5, không phân biệt dấu) và ngữ nghĩa, kết hợp hybrid.
5. Trả lời chỉ dựa trên ngữ cảnh truy xuất được, kèm citation và nhãn mức tin cậy.
6. Kiểm mẫu chất lượng nguồn và đo retrieval/answer bằng golden set.

**Ngoài phạm vi MVP:** an lá số, tính sao/cung, dự báo hoặc luận đoán cho cá nhân, đăng nhập nhiều tầng, hệ phân tán.

**Nguyên tắc:**
- PDF/sách là nguồn thẩm định gốc; Excel là bản ghi tri thức đã chuẩn hóa; SQLite là cơ sở vận hành; Qdrant là chỉ mục có thể tái tạo.
- **Giữ ba tiếng nói:** không gộp hay "dung hòa" nội dung giữa các sách. Câu trả lời luôn nêu "theo sách X" và tách theo sách.
- **Mô tả quan điểm của sách, không khẳng định là sự thật** (Tử Vi là hệ thống diễn giải, không phải kết luận khoa học hay y khoa).
- Không để LLM tạo ra tri thức canonical. LLM chỉ tổng hợp từ ngữ cảnh đã truy xuất.
- Không bịa trang. Nguồn nào chưa đối chiếu thì UI nói rõ mức xác minh. Không trích nguyên văn dài tài liệu có bản quyền.

## 1. Hiện trạng dữ liệu (từ khảo sát file thật)

### 1.1 Số liệu chính

| | NPL — Nguyễn Phát Lộc | BD — Bửu Đình | DAU — Đẩu Số Toàn Thư |
|---|---|---|---|
| Bản ghi active | 2.191 | 4.450 | 3.815 |
| Nguồn văn bản | extraction từ PDF | Tesseract OCR (7 PDF) | text layer |
| `Release_Status` | LOCKED_V1_0 | DRAFT_NOT_RELEASED | DRAFT_NOT_RELEASED |
| Có Subject/Predicate/Object | 100% | 100% | ~9% |
| Độ dài text (trung vị) | 106 ký tự | 129 | 37 |
| Bản ghi dưới 40 ký tự | 4 | 289 | 2.010 |
| Cách ghi trang | PDF page | `P7:36` (phần:trang, trang theo từng phần) | PDF page (có cả trang in) |
| Trang in (`Printed_Page`) | trống | trống | có |

Toàn bộ: **10.456 bản ghi active**, ID duy nhất, 100% nối được sang `EVIDENCE` và đều có `PDF_Page`. 33 evidence trỏ về ID đã gộp, đều tra được qua `CANONICAL_ID_REDIRECTS`.

### 1.2 Các phát hiện làm thay đổi thiết kế

1. **Chưa có dấu vết người duyệt nào.** `Reviewer` và `Review_Date` trống 100% ở cả ba sách; mọi trạng thái vẫn là pending. Sheet OVERVIEW ghi "User states all checks completed" nhưng nói rõ không nâng trạng thái cũ. Gate "approved + verified" của v1.0 sẽ index **0 bản ghi**.
2. **Evidence của NPL là tổng hợp từ extraction** (`SYNTHESIZED_FROM_EXTRACTION`), không phải evidence độc lập.
3. **Trang của BD là số theo từng phần**, và `Printed_Page` trống ở NPL và BD. Schema trích dẫn phải có `part_number`.
4. **DAU và BD có nhiều bản ghi vụn:** 2.010 bản ghi DAU ngắn hơn 40 ký tự (nhiều câu thơ/phú rời); `SEMANTIC_REVIEW_WORKLIST` còn 1.650 mục OPEN loại `POSSIBLE_VERSE_OR_CONTINUATION_FRAGMENT`; BD có 442 bản ghi `PAGE_OR_PARAGRAPH_CONTINUATION` (câu bị cắt giữa chừng).
5. **BD là OCR chưa kiểm:** 1.759 bản ghi `OCR_REVIEW_REQUIRED`, 1.512 mục trong `REVIEW_QUEUE`; `Source_Certainty` là UNKNOWN/UNVERIFIED, `Conflict_Status` chưa đánh giá. DAU cũng chưa đánh giá conflict. Không dùng các cột này để phát hiện "sách mâu thuẫn".
6. **Từ vựng còn mỏng:** `VOCABULARY` có 669 dòng, 477 thuật ngữ khác nhau, chỉ 7,2% dòng có alias, 45 dòng `APPROVED_TERM`.
7. **Dedup đã làm xong ở mức chính xác:** 33 bản ghi trùng được gộp (có log), 34 trường hợp chồng lấn khác chương được giữ nguyên, 21 trường hợp tương tự được giữ lại để xem xét. Không dedup chéo giữa các sách. Sau đó vẫn còn 89 bản ghi có văn bản giống hệt nhau trong cùng sách (49 BD, 38 DAU, 2 NPL), có thể ở khác trang.

### 1.3 Trust tier (thay cho gate "approved + verified")

Tier được **suy ra từ dữ liệu** bằng quy tắc trong `column_mapping.yaml`, khớp quy tắc đầu tiên thắng:

| Tier | Điều kiện | Số bản ghi | Mặc định | Nhãn UI |
|---|---|---|---|---|
| 1 | NPL | 2.191 | index | Đối chiếu theo trang PDF, chưa kiểm thủ công |
| 2 | DAU, trừ `OCR_REVIEW_REQUIRED` | 3.798 | index | Text layer, chưa duyệt ngữ nghĩa |
| 3 | BD, trừ `OCR_REVIEW_REQUIRED` | 2.691 | index (bật/tắt bằng config) | OCR chưa kiểm, có thể sai chính tả |
| 9 | `OCR_REVIEW_REQUIRED` (BD 1.759, DAU 17) | 1.776 | **loại khỏi index** | — |

Tổng số bản ghi được index ban đầu: **8.680**. Muốn chặt hơn thì đổi `enabled_tiers` trong YAML, không sửa code.

`verification_status` (mức xác minh thủ công) là một lớp riêng, **nâng tier lên "đã kiểm"** khi có kết quả kiểm mẫu hoặc duyệt từng bản ghi (mục 3.4). Mặc định mọi bản ghi là `unverified`.

## 2. Stack đề xuất

- Python 3.11+; FastAPI, Pydantic, SQLAlchemy (tạo bảng bằng `create_all`, **bỏ Alembic** cho MVP); pytest, ruff.
- Streamlit cho UI hỏi đáp, tra cứu và trang review. **Streamlit gọi thẳng service layer** của backend (cùng repo); FastAPI giữ làm lớp API mỏng để test và demo `/search`, `/chat/ask`.
- pandas + openpyxl đọc Excel. **Không cần PyMuPDF/OCR** trong MVP: dữ liệu đã được trích xuất sẵn trong Excel.
- SQLite lưu dữ liệu vận hành; **FTS5 bắt buộc** (không phải tùy chọn) làm baseline từ khóa, có bỏ dấu tiếng Việt.
- Qdrant local persistent cho dense vector, đặt sau interface `VectorStore` để có thể thay bằng numpy/FAISS (corpus nhỏ, vài nghìn chunk). `BAAI/bge-m3` (1024D) là embedding đề xuất; kiểm tra RAM/tốc độ trên máy thật. Đổi model thì rebuild toàn bộ index, không dùng chung index giữa hai model.
- LLM qua adapter `LLMProvider`, không gắn một hãng; chỉ gọi LLM sau khi retrieval đủ ngữ cảnh.
- `.env` giữ credentials, `.env.example` trong Git. Không commit API key và file sách/Excel có bản quyền lên kho public.

## 3. Kiến trúc dữ liệu

### 3.1 Bảng chính

| Bảng | Trường chính |
|---|---|
| `books` | `book_code` (PK: NPL/BD/DAU), `source_id`, `title`, `author`, `total_pages`, `source_status` |
| `book_parts` | `source_id`, `part_number`, `pdf_file`, `total_pdf_pages` (chỉ BD có 7 phần) |
| `knowledge_items` | `knowledge_id` (= `Canonical_ID`, ID ổn định), `book_code`, `knowledge_type`, `taxonomy_code`, `subject`, `predicate`, `object`, `condition_context`, `text` (= `Canonical_Knowledge`), `chapter`, `source_certainty`, `review_flag`, `release_status`, `validation_status`, `trust_tier`, `content_hash`, `version`, `updated_at` |
| `knowledge_pages` | `knowledge_id`, `part_number` (nullable), `pdf_page` — tách từ `PDF_Pages` (có thể nhiều trang) |
| `evidences` | `evidence_id`, `knowledge_id`, `book_code`, `part_number`, `pdf_page`, `printed_page` (nullable), `original_text`, `ocr_legibility`, `evidence_method`, `origin`, `source_review_status`, `verification_status` (`unverified\|sample_verified\|verified\|rejected`), `reviewer`, `reviewed_at`, `review_note` |
| `id_redirects` | `original_id`, `active_id` |
| `chunks` | `chunk_id`, `book_code`, `chapter`, `chunk_text`, `embed_text`, `trust_tier`, `chunking_version`, `embedding_model`, `indexed_at`, `content_hash` |
| `chunk_members` | `chunk_id`, `knowledge_id`, `position` |
| `vocabulary` / `term_aliases` | `term`, `entity_type`, `taxonomy_code`, `alias`, `alias_source` (`excel\|auto\|manual`) |
| `import_runs` | `run_id`, `file_name`, `file_sha256`, `started_at`, `finished_at`, `rows_read`, `rows_imported`, `rows_rejected`, `report_path` |
| `audit_samples` | `sample_id`, `knowledge_id`, `auditor`, `text_matches_source` (Y/N/partial), `page_correct` (Y/N), `ocr_error` (Y/N), `note`, `audited_at` |
| `evaluation_cases` | `case_id`, `question`, `type`, `expected_knowledge_ids`, `expected_status`, `author` |
| `chat_logs` | tùy chọn, có thể tắt |

**Lưu ý:**
- Tên cột Excel ↔ trường DB do `column_mapping.yaml` quy định, không gắn cứng trong code.
- `knowledge_id` dùng thẳng `Canonical_ID` (đã ổn định, đã có redirect). Không dùng số dòng Excel làm khóa. Một chunk có thể gồm nhiều bản ghi nên cần `chunk_members`.
- Evidence trỏ tới ID đã gộp thì tra `id_redirects` để gắn về bản ghi active; không xóa evidence.
- Sửa nội dung thì tăng `version`, upsert và reindex. Loại khỏi tier được index hoặc bị từ chối thì phải gỡ chunk liên quan khỏi Qdrant.

### 3.2 Quy tắc chất lượng dữ liệu

- `Canonical_ID`, `Canonical_Knowledge`, `Book_Code`, `PDF_Pages` không rỗng; UTF-8 hợp lệ; `PDF_Pages` parse được theo `page_parsing` (BD: `P<phần>:<trang>`).
- Số bản ghi theo sách phải khớp `expected_counts`; lệch thì dừng import.
- Chỉ index bản ghi thuộc `enabled_tiers` **và** có ít nhất một evidence. Bản ghi tier 9 không được vào index.
- Văn bản giống hệt trong cùng sách: giữ cả hai (có thể ở khác trang), gắn `duplicate_text_group`; khi truy xuất chỉ hiện một bản ghi đại diện kèm các trang còn lại.
- Xung đột giữa các sách được giữ riêng và gắn nhãn theo sách; không ép hợp nhất.
- Báo cáo sinh ra mỗi lần import: `tier_report.csv`, `short_records.csv`, `unparsed_pages.csv`, `duplicate_text_groups.csv`, `import_summary.json`.

## 4. Luồng xử lý dữ liệu (offline ingestion)

1. `scripts/inspect_excel.py`: kiểm tra mapping và chất lượng file (exit code khác 0 nếu lệch). Chạy lại mỗi khi Excel thay đổi.
2. `scripts/import_excel.py`: đọc các sheet được dùng theo mapping; nạp `books`, `book_parts`, `knowledge_items`, `knowledge_pages`, `evidences`, `id_redirects`, `vocabulary`. Idempotent: import lần hai cùng file (cùng SHA-256) không tạo bản ghi trùng; khác SHA thì so `content_hash` để upsert và tăng `version`.
3. Chuẩn hóa nhẹ (khoảng trắng, Unicode NFC), giữ bản gốc để đối chiếu.
4. Gán `trust_tier` theo quy tắc trong YAML; ghi `tier_report.csv`.
5. Gán `duplicate_text_group` từ hash văn bản chuẩn hóa. Dedup đã làm ở Excel (`DEDUPE_LOG`, `CANONICAL_ID_REDIRECTS`); import chỉ đọc, không dedup lại.
6. Chunking (mục 4.1), tạo `chunks` và `chunk_members`.
7. Embedding theo batch, upsert Qdrant bằng `chunk_id` ổn định; tạo chỉ mục FTS5.
8. Lưu manifest `model_name`, `model_version`, `chunking_version`, `index_version`, `enabled_tiers`. Có cơ chế reindex khi dữ liệu, model hoặc tier thay đổi.
9. Đối soát: số chunk đã index = số chunk eligible; mọi `knowledge_id` trong chunk đều tồn tại và thuộc tier được bật; lấy mẫu ngẫu nhiên so với nguồn.

### 4.1 Chunking (theo `chunking` trong YAML; tham số là đề xuất, chỉnh theo golden set)

- **Loại bản ghi tier 9 trước khi gộp**; chunk không bắc cầu qua bản ghi bị loại.
- **NPL:** một bản ghi = một chunk (đã có cấu trúc, độ dài ổn định).
- **DAU và BD:** gộp các bản ghi liền kề trong cùng sách theo thứ tự `knowledge_id`, nhóm theo `(part_number, pdf_page, chapter)`:
  - cộng dồn đến khi đạt `min_chars` (150), không vượt `max_chars` (600) khi gộp; một bản ghi đơn lẻ dài hơn vẫn giữ nguyên, không cắt;
  - bản ghi gắn `PAGE_OR_PARAGRAPH_CONTINUATION` (BD) được gộp với bản ghi kế tiếp kể cả khi sang trang, miễn cùng chương;
  - phần dư ngắn hơn `min_chars` gộp vào chunk trước trong cùng nhóm.
- **Giả định cần kiểm ở ticket chunker:** thứ tự `knowledge_id` trùng với thứ tự đọc (trang không giảm trong từng sách). Nếu không, sắp xếp lại theo `(part_number, pdf_page, id)`.
- **Văn bản để embed:** `{chapter} | {subject} | {text}`, ghép thêm alias của thuật ngữ nhận diện được. `Original_Text` trong evidence chỉ dùng để hiển thị đoạn trích **ngắn** (đề xuất ≤ 300 ký tự), không đưa vào embedding.
- `chunk_id` = `knowledge_id` với chunk một-bản-ghi; với chunk gộp là hash của danh sách `knowledge_id` + `chunking_version`. Metadata: `book_code`, `chapter`, trang đầu/cuối (kèm `part_number`), `trust_tier`, danh sách `knowledge_id`.

## 5. Luồng hỏi đáp (online query)

1. Nhận câu hỏi tiếng Việt; giới hạn độ dài; lọc yêu cầu ngoài phạm vi, đặc biệt yêu cầu luận lá số cá nhân (trả `out_of_scope` kèm giải thích).
2. Chuẩn hóa query: Unicode, bỏ dấu cho FTS, mở rộng alias và nhận diện thực thể (sao, cung) từ `vocabulary`. Xử lý nhập nhằng: "Tử Vi" vừa là tên sao vừa là tên môn học; ưu tiên diễn giải theo ngữ cảnh câu hỏi, không tự ý đổi nghĩa.
3. **Truy xuất theo từng sách:** lấy top-N ứng viên **mỗi sách** (đề xuất N = 8) từ dense và từ FTS5, hợp nhất bằng RRF, sau đó chọn tối đa 5–7 ngữ cảnh sao cho mỗi sách có đại diện nếu vượt ngưỡng. Reranker chỉ thêm nếu Recall@5 chưa đạt.
4. Với từng `chunk_id`, tra SQLite để đảm bảo mọi thành viên vẫn thuộc `enabled_tiers` và có evidence; gộp kết quả trùng văn bản (`duplicate_text_group`).
5. Không đủ căn cứ (không chunk nào vượt ngưỡng đã hiệu chỉnh): trả `insufficient_evidence`, không để LLM tự phỏng đoán. Ngưỡng hiệu chỉnh trên golden set, không dùng một con số tùy ý.
6. Xây prompt: câu hỏi + danh sách ngữ cảnh gắn số `[1]`, `[2]` và metadata (sách, phần, trang, tier). Mọi nội dung truy xuất là dữ liệu không tin cậy, không phải chỉ thị.
7. LLM tổng hợp **chỉ dựa trên ngữ cảnh**, **trình bày tách theo sách** ("Theo Nguyễn Phát Lộc…", "Theo Bửu Đình…"), nói rõ khi các sách khác nhau, dùng giọng "theo sách" thay vì khẳng định. Không đưa lời khuyên y khoa/tài chính/quyết định cá nhân.
8. Kiểm tra tự động citation: mọi `[n]` phải nằm trong ngữ cảnh đã đưa; phát hiện câu không có citation; log thông tin vận hành không nhạy cảm; trả JSON.
9. UI hiện câu trả lời, thẻ nguồn (sách, phần, trang PDF, nhãn tier, đoạn trích ngắn có thể mở), và trạng thái "không đủ căn cứ" khi cần.

### 5.1 Hợp đồng JSON gợi ý

Request `POST /api/v1/chat/ask`:
```json
{"question":"Theo các sách, sao Thiên Phủ được giải nghĩa thế nào?","top_k":5}
```
Response:
```json
{
  "answer":"Theo Nguyễn Phát Lộc ... [1]. Theo Tử Vi Đẩu Số Toàn Thư ... [2].",
  "status":"answered",
  "citations":[{
    "ref":"1",
    "knowledge_ids":["KN-000042"],
    "book_code":"NPL",
    "book_title":"<lấy từ dữ liệu thật>",
    "part_number":null,
    "pdf_page_start":10,
    "pdf_page_end":10,
    "printed_page":null,
    "trust_tier":1,
    "verification_status":"unverified",
    "ui_badge":"Đối chiếu theo trang PDF, chưa kiểm thủ công",
    "excerpt":"<đoạn trích ngắn>"
  }],
  "retrieval":{"num_candidates":24,"num_contexts":5,"books_covered":["NPL","DAU"]},
  "request_id":"<UUID>"
}
```
`status` ∈ `answered | insufficient_evidence | out_of_scope | error`. Nếu không đủ căn cứ thì `citations=[]` hoặc chỉ là nguồn gợi ý được phân biệt rõ; không dựng citation giả.

## 6. API cần code

| Endpoint | Method | Mục tiêu | Priority |
|---|---|---|---|
| `/health` | GET | Health-check | P0 |
| `/api/v1/search` | POST | Tìm kiếm theo sách, trả chunk + evidence + điểm, không gọi LLM | P0 |
| `/api/v1/chat/ask` | POST | RAG answer và citations | P0 |
| `/api/v1/knowledge` | GET | Danh sách/tìm theo term, sách, tier, trạng thái | P0 |
| `/api/v1/knowledge/{id}` | GET | Chi tiết bản ghi + evidence + chunk chứa nó | P0 |
| `/api/v1/index/rebuild` | POST | Tái tạo index theo `enabled_tiers` (admin) | P0 |
| `/api/v1/knowledge/{id}/review` | PATCH | Ghi kết quả kiểm/duyệt (`verification_status`, ghi chú) | P1 |
| `/api/v1/audit/sample` | GET/POST | Lấy mẫu kiểm phân tầng, ghi kết quả | P1 |
| `/api/v1/stats` | GET | Thống kê tier, sách, trạng thái kiểm | P1 |
| `/api/v1/ingest/preview` · `/commit` | POST | Import qua API (script `import_excel.py` là đường chính của MVP) | P2 |

Chạy đánh giá bằng script `scripts/evaluate.py`, không cần endpoint. **Không công khai import/rebuild trên Internet khi chưa có auth.** MVP chạy localhost; bản public cần xác thực, rate limit, CORS cụ thể.

## 7. Cấu trúc repository

```text
kms-tuvi/
├── README.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── configs/
│   ├── column_mapping.yaml     # đã có: mapping + trust tier + chunking
│   ├── taxonomy.yaml
│   └── retrieval.yaml          # N mỗi sách, RRF, ngưỡng, số ngữ cảnh
├── docs/
│   ├── data_dictionary.md      # sinh tự động, không sửa tay
│   ├── KMS_TuVi_Development_Plan.md
│   └── wiig_mapping.md
├── data/
│   ├── raw/                    # Excel + sách (gitignored, không push public)
│   ├── processed/
│   ├── reports/
│   └── qdrant/                 # gitignored
├── backend/app/
│   ├── main.py
│   ├── core/config.py
│   ├── api/{health,knowledge,index,search,chat,audit,stats}.py
│   ├── db/{models,session}.py
│   ├── schemas/{knowledge,chat}.py
│   ├── services/
│   │   ├── mapping.py          # đọc column_mapping.yaml
│   │   ├── excel_reader.py
│   │   ├── normalize.py        # NFC, bỏ dấu, alias
│   │   ├── tiering.py          # gán trust_tier
│   │   ├── pages.py            # parse PDF_Pages
│   │   ├── chunker.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   ├── fts.py
│   │   ├── retriever.py
│   │   ├── llm_provider.py
│   │   ├── rag.py
│   │   └── citation_validator.py
│   └── repositories/
├── frontend/
│   ├── app.py
│   └── pages/{chat,search,review,stats}.py
├── scripts/
│   ├── inspect_excel.py        # đã có
│   ├── import_excel.py
│   ├── build_index.py
│   ├── make_audit_sample.py
│   └── evaluate.py
├── evaluations/
│   ├── golden_questions.csv
│   └── results/
└── tests/
    ├── test_mapping.py
    ├── test_pages.py
    ├── test_tiering.py
    ├── test_import_idempotent.py
    ├── test_chunking.py
    ├── test_reindex.py
    ├── test_retrieval.py
    ├── test_citation_validator.py
    └── test_chat_api.py
```

## 8. Lộ trình 4 sprint (nhóm 2–3 người)

Dữ liệu đã được canonical hóa và có evidence nên phần nhập liệu nhẹ hơn v1.0; công sức dồn vào chunking, retrieval và kiểm mẫu. Mục tiêu là **có lát cắt dọc chạy được (search có đo kết quả) ở cuối Sprint 2**, trước khi làm UI.

| Sprint | Ticket | Công việc | Kết quả kiểm chứng |
|---|---|---|---|
| S1 | T01 | Repo, môi trường, `.env.example`, ruff/pytest | `pytest` chạy; `/health` trả 200 |
| S1 | T02 ✔ | `inspect_excel.py` + `column_mapping.yaml` + `data_dictionary.md` | **Đã xong**; 70/70 cột khớp, số lượng khớp kỳ vọng |
| S1 | T03 | Schema SQLAlchemy, seed `books`/`book_parts` | Bảng tạo đúng; seed đủ 3 sách và 7 phần BD |
| S1 | T04 | `import_excel.py`: đọc mapping, parse trang, redirects, gán tier, báo cáo | 10.456 bản ghi vào DB; import lần 2 không tạo trùng; `tier_report.csv` khớp mục 1.3 |
| S1 | T05 | Chunker v0 (NPL 1:1; DAU/BD gộp), kiểm giả định thứ tự | Mỗi chunk truy được về bản ghi/evidence; báo cáo phân bố độ dài chunk |
| S2 | T06 | Embedding adapter, Qdrant local, `build_index.py` incremental, manifest | Sửa/loại bản ghi không để lại vector cũ |
| S2 | T07 | FTS5 (bỏ dấu) + vocabulary/alias + nhận diện thực thể | Tìm "tu vi", "Tử Vi" cho kết quả tương đương |
| S2 | T08 | Retriever: top-N mỗi sách, hybrid RRF, kiểm tra tier; `/search` | Kết quả có đủ sách khi liên quan |
| S2 | T09 | Golden set v0 (30 câu) + `evaluate.py` | Có Recall@5 baseline cho FTS vs dense vs hybrid |
| S3 | T10 | `make_audit_sample.py`, ghi kết quả kiểm mẫu (100 bản ghi mỗi sách) | Có tỷ lệ đúng trang/đúng văn bản theo sách |
| S3 | T11 | LLM provider, mock, prompt theo sách, citation validator | Test chạy không cần API key |
| S3 | T12 | `/chat/ask`: abstention, out_of_scope, lỗi provider | JSON đúng schema kể cả khi provider lỗi |
| S3 | T13 | Golden set đầy đủ (40–50 câu) + đo toàn bộ metric | Báo cáo theo sách và theo tier |
| S4 | T14 | Streamlit: Chat + Search (nhãn tier, thẻ nguồn) | Hỏi đáp, mở nguồn được |
| S4 | T15 | Streamlit: Review + Data Status | Ghi kiểm mẫu, xem thống kê tier |
| S4 | T16 | Sửa lỗi hồi quy, README, build demo | Người khác clone và chạy được |
| S4 | T17 | Ánh xạ Wiig KM Cycle → code → evidence (**viết song song từ S1**) | Bảng Build/Hold/Pool/Use |

**Phân công gợi ý:** A — dữ liệu (T03–T05, T10); B — retrieval/RAG (T06–T08, T11–T12); C — golden set, UI, test, tài liệu (T09, T13–T17). Cần thống nhất interface giữa A/B ở T05 (chunk) và B/C ở T08 (search). Nếu chỉ có một người code: giữ thứ tự phụ thuộc, hoãn T15 và nhãn tier tinh chỉnh.

**Có thể cắt/hoãn nếu thiếu thời gian:** reranker, `/ingest/*` API, `/index/rebuild` giao diện, `chat_logs`, trang Review (dùng script).

## 9. Kiểm mẫu chất lượng nguồn (thay cho "review toàn bộ")

Không thể duyệt tay 10.456 bản ghi; thay bằng kiểm mẫu phân tầng để biết chất lượng thật và báo cáo trung thực:

- Lấy **100 bản ghi ngẫu nhiên mỗi sách** (đề xuất; điều chỉnh theo nhân lực), phân tầng theo chương hoặc trang để không dồn một chỗ. Mẫu cố định bằng random seed để tái lập.
- Mỗi bản ghi người kiểm đối chiếu với ảnh PDF và ghi: `text_matches_source` (Y/N/partial), `page_correct` (Y/N), `ocr_error` (Y/N), ghi chú.
- Một phần mẫu (đề xuất 20%) được hai người kiểm độc lập để đo mức đồng thuận.
- Kết quả báo cáo kèm cỡ mẫu, theo từng sách. Nếu tỷ lệ lỗi của một tier vượt ngưỡng nhóm đặt ra, hạ tier đó khỏi `enabled_tiers` hoặc ưu tiên review thêm.
- Bản ghi được duyệt thủ công thì ghi `verification_status` và hiển thị nhãn "đã kiểm" trong UI.

## 10. Definition of Done (DoD) / Gate

**Gate 1 — Data ready:** `inspect_excel.py` thoát mã 0; import khớp `expected_counts`; 10.456 bản ghi vào DB, 100% parse được trang; không bản ghi tier 9 nào xuất hiện trong index; import lần 2 không sinh bản ghi mới.

**Gate 2 — Retrieval ready:** kết quả top-k chứa `knowledge_id`, evidence, điểm và nhãn tier; có đại diện từng sách khi liên quan; cập nhật hoặc loại bản ghi không để lại chunk cũ; đã so baseline FTS vs dense vs hybrid.

**Gate 3 — RAG ready:** mock LLM chạy không cần API key; citation chỉ trỏ tới ngữ cảnh thật; câu ngoài corpus và yêu cầu luận lá số cá nhân được xử lý rõ; API trả đúng schema ngay cả khi provider lỗi.

**Gate 4 — Demo ready:** hỏi ít nhất 5 câu theo chủ đề, mở được nguồn; một câu thiếu dữ liệu trả `insufficient_evidence`; một câu so sánh hai sách cho kết quả tách theo sách; hiển thị được số bản ghi theo tier và kết quả kiểm mẫu.

### 10.1 Bộ đánh giá

- **Golden set 40–50 câu**, chia theo sách và loại: hỏi thuật ngữ, diễn giải, so sánh giữa sách, diễn đạt lại (paraphrase), câu kiểu thơ/phú cho DAU, câu nói thông thường (không dùng Hán Việt), câu ngoài corpus, câu mơ hồ ("Tử Vi" là sao hay môn học), yêu cầu luận lá số cá nhân.
- **Tránh thiên lệch:** ít nhất 1/3 câu do người **chưa xem** bản ghi đáp án viết, dùng từ phổ thông. Ít nhất 2 người kiểm tra thủ công câu hỏi, đáp án và nguồn.
- **Recall@5:** tỷ lệ câu có ít nhất một evidence đúng nằm trong top 5 (câu đa nguồn: thêm all-relevant recall). Báo theo sách và theo tier.
- **Citation validity:** tỷ lệ citation trỏ tới chunk/evidence có thật trong ngữ cảnh đã đưa (không phải đúng về ngữ nghĩa).
- **Groundedness/faithfulness:** tỷ lệ luận điểm được ngữ cảnh hỗ trợ; chấm tay, đối chiếu Ragas nếu dùng.
- **Abstention accuracy:** từ chối đúng câu ngoài phạm vi/thiếu căn cứ, không từ chối thừa câu có đáp án.
- **Latency p50/p95** theo máy và loại LLM.
- **Mục tiêu đề xuất để thử nghiệm, không phải kết quả:** Recall@5 ≥ 0,8; citation validity = 100% (về sự tồn tại); 100% bản ghi tier 9 bị chặn khỏi index; 0 key bị lộ. Điều chỉnh sau khi có baseline; không tuyên bố đạt khi chưa đo.

## 11. Kịch bản demo 5–7 phút

1. Giới thiệu 3 cuốn sách, 3 tiếng nói, và lý do cần cơ sở tri thức có cấu trúc.
2. Mở bảng tổng quan: tổng bản ghi, phân bố trust tier, số bản ghi được index, kết quả kiểm mẫu.
3. Chọn một bản ghi, mở nguồn (sách, phần, trang PDF) và đối chiếu với PDF gốc.
4. Hỏi một câu dùng đúng thuật ngữ; cho thấy top retrieval theo sách và câu trả lời có trích dẫn.
5. Hỏi cùng ý bằng cách nói thông thường; cho thấy semantic và hybrid retrieval.
6. Hỏi một câu so sánh giữa hai sách; cho thấy câu trả lời tách theo sách, không hợp nhất.
7. Hỏi câu ngoài dữ liệu và một yêu cầu luận lá số cá nhân; hệ thống từ chối.
8. Chỉ rõ Wiig Build (import/chuẩn hóa/kiểm mẫu), Hold (SQLite + tri thức canonical), Pool (retrieval), Use (RAG UI). Báo cáo kết quả evaluation và giới hạn (nguồn OCR chưa kiểm, chưa có duyệt ngữ nghĩa toàn bộ).

## 12. Bootstrapping tối thiểu

```bash
# từ thư mục dự án
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install fastapi 'uvicorn[standard]' pydantic sqlalchemy \
    pandas openpyxl pyyaml qdrant-client sentence-transformers \
    streamlit httpx python-dotenv pytest ruff
# Cài thêm SDK nhà cung cấp LLM; khóa phiên bản sau khi kiểm thử.

# 1) kiểm tra Excel + mapping, sinh data_dictionary.md
python scripts/inspect_excel.py \
  --excel data/raw/TuVi_KMS_3Books_CANONICAL_MASTER_DEDUP_v1_0.xlsx

# 2) sau khi có import_excel.py / build_index.py
python scripts/import_excel.py
python scripts/build_index.py

# 3) chạy backend và UI (hai terminal)
uvicorn backend.app.main:app --reload --port 8000
streamlit run frontend/app.py
```

Kiểm tra trước khả năng tải BGE-M3 trên máy đang dùng (RAM/dung lượng đĩa). Nếu không đủ, thử embedding nhỏ hơn hỗ trợ tiếng Việt và đánh giá Recall@5; không dùng chung index giữa hai embedding khác model/dimension.

## 13. Rủi ro và kiểm soát

- **Chưa có dấu vết người duyệt:** hiển thị nhãn tier trên UI, báo cáo kết quả kiểm mẫu, không gọi dữ liệu là "đã duyệt". Nhóm cần xác nhận việc review đã làm và, nếu có, ghi vào cột trạng thái của file nguồn.
- **OCR của BD sai chính tả/dấu:** FTS bỏ dấu, hybrid, loại bản ghi tier 9, kiểm mẫu theo sách; cho phép tắt tier 3 bằng cấu hình.
- **Bản ghi vụn (DAU, BD):** chunk gộp; theo dõi tỷ lệ chunk còn ngắn trong báo cáo chunker.
- **Evidence NPL là tổng hợp từ extraction:** coi là đối chiếu theo trang PDF, không phải evidence độc lập; kiểm mẫu NPL cùng cách với các sách khác.
- **Sách mâu thuẫn/ba tiếng nói:** truy xuất và trình bày theo từng sách; không dùng `Conflict_Status` chưa đánh giá làm căn cứ.
- **RAG hallucination:** gate tier, prompt chỉ từ ngữ cảnh, citation validator, golden set, abstention.
- **Embedding chưa hợp tiếng Việt/Hán Việt:** golden set có paraphrase và câu nói thông thường, từ điển alias (hiện thưa), hybrid FTS + dense.
- **Nhập nhằng thuật ngữ** ("Tử Vi" là sao hay môn học): nhận diện thực thể từ vocabulary, thêm câu mơ hồ vào golden set.
- **Excel thay đổi:** `inspect_excel.py` + mapping + SHA-256 + import idempotent + rebuild index.
- **Bản quyền / API key:** không push public sách và Excel, không trích dài, giới hạn truy cập nội dung sách; không commit key.
- **Prompt injection trong nguồn:** coi mọi đoạn truy xuất là dữ liệu; chỉ làm theo chỉ thị của hệ thống.
- **Phạm vi nội dung:** không luận đoán cho cá nhân, không đưa lời khuyên y khoa/tài chính; giọng "theo sách".
- **Deploy:** ban đầu chỉ localhost; bản public cần auth cho admin, rate limit, sao lưu DB, bảo vệ storage.

## 14. Thứ tự bắt đầu code

1. ✔ Khảo sát Excel thật, `column_mapping.yaml`, `data_dictionary.md` (đã xong).
2. Chốt các quyết định mở ở Phụ lục B (đặc biệt: xác nhận review đã làm, bật/tắt tier 3).
3. Tạo schema (T03) và `import_excel.py` (T04) kèm test idempotent; đối chiếu `tier_report.csv` với mục 1.3.
4. Chunker (T05), kiểm giả định thứ tự đọc, xem phân bố độ dài chunk.
5. Search baseline FTS5 và dense; đo trên golden set v0 **trước khi gọi LLM** (T06–T09).
6. Citation validator, mock LLM, `/chat/ask` với abstention (T11–T12).
7. Giao diện sau khi API ổn định: Chat + Search trước, Review/Stats sau.
8. Chạy evaluation đầy đủ, sửa chunking/retrieval/prompt theo lỗi thực tế.

## Phụ lục A — Thay đổi so với v1.0

| Mục | v1.0 | v1.1 | Lý do |
|---|---|---|---|
| Gate dữ liệu | `approved` + evidence `verified` | `trust_tier` suy ra từ dữ liệu; `verification_status` là lớp riêng | Không bản ghi nào có `Reviewer`; gate cũ index 0 bản ghi |
| Schema trích dẫn | `page_start` số nguyên | `part_number` + `pdf_page` + `printed_page` | Trang BD theo từng phần; trang in trống ở NPL/BD |
| Khóa bản ghi | cấp ID mới, `source_excel_row` | dùng `Canonical_ID` | ID đã ổn định, có redirect |
| Dedup | tự dedup khi import | đọc kết quả có sẵn; chỉ gán nhóm trùng văn bản | Excel đã dedup và có log |
| Chunking | một dòng ngắn ghi chú | thuật toán gộp + văn bản embed + `chunk_members` | DAU có 2.010 bản ghi < 40 ký tự |
| Truy xuất | top-k chung | top-N mỗi sách + hybrid | Giữ ba tiếng nói |
| Phát hiện mâu thuẫn | dựa trường trạng thái | trình bày theo sách | `Conflict_Status` BD/DAU chưa đánh giá |
| FTS5 | tùy chọn | bắt buộc, bỏ dấu | OCR BD sai dấu; làm baseline |
| Alembic, PyMuPDF | có | bỏ | Không cần cho MVP |
| Review | duyệt từng bản ghi | kiểm mẫu phân tầng | Không thể duyệt 10.456 bản ghi |
| Golden set | tạo từ bản ghi đã duyệt | một phần do người chưa xem đáp án viết; thêm câu thơ, đời thường, mơ hồ, luận cá nhân | Tránh Recall@5 cao ảo |
| Lộ trình | UI ở S4, chat ở S3 | lát cắt dọc (search có đo) cuối S2; T17 chạy song song | Giảm rủi ro dồn về cuối |

## Phụ lục B — Quyết định cần nhóm chốt

1. **Trạng thái review:** OVERVIEW ghi tất cả kiểm tra đã hoàn tất nhưng không có `Reviewer`/`Review_Date`. Đã review thật chưa? Nếu rồi, ghi vào cột trạng thái nguồn để hệ thống nâng tier.
2. **Tier 3 (BD, OCR chưa kiểm):** bật mặc định hay tắt cho đến khi có kết quả kiểm mẫu?
3. **Nhân lực kiểm mẫu:** ai kiểm, bao nhiêu bản ghi mỗi người (mục 9).
4. **Nhà cung cấp LLM và ngân sách API.**
5. **Phần cứng cho embedding** (BGE-M3 hay model nhỏ hơn).
6. **Quy ước hiển thị trang:** chốt cách ghi "Phần N, PDF tr. X" cho BD và "PDF tr. X" cho NPL/DAU.

**Cơ sở tham khảo kỹ thuật:** https://qdrant.tech/documentation/quickstart/ · https://huggingface.co/BAAI/bge-m3 · https://fastapi.tiangolo.com/tutorial/first-steps/ · https://docs.streamlit.io/develop/concepts/multipage-apps · https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/
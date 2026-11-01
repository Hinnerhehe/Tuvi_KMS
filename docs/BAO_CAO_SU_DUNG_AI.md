# Báo cáo sử dụng AI trong dự án KMS Tử Vi

> Đây là báo cáo trạng thái trước đợt sửa theo phản hồi giảng viên. Thay đổi mới về tiểu hạn, phân tích sao, truy xuất và timeout AI được ghi tại [HOROSCOPE_FEEDBACK_FIXES.md](HOROSCOPE_FEEDBACK_FIXES.md).

**Ngày lập:** 31/10/2026  
**Phạm vi:** Mã nguồn và tài liệu hiện có trong repository; gồm chức năng hỏi đáp tri thức ba sách, ứng dụng luận giải lá số và việc dùng AI hỗ trợ phát triển.  
**Cách hiểu:** “Đã triển khai” là có mã nguồn/luồng chạy; không đồng nghĩa chất lượng nội dung AI đã được nghiệm thu.

## 1. Tóm tắt

Dự án dùng AI ở **hai chức năng cho người dùng**: (1) mô hình ngôn ngữ Gemini diễn đạt câu trả lời hỏi đáp dựa trên đoạn sách truy xuất được; (2) Gemini tạo bài luận giải cá nhân từ đặc trưng lá số và ngữ cảnh sách. Ngoài ra, dự án có **embedding** để hỗ trợ tìm kiếm ngữ nghĩa; phần hỏi đáp có thể dùng mô hình embedding cục bộ hoặc Gemini tùy cấu hình. Thuật toán an sao, trích xuất đặc trưng, tìm kiếm FTS5, kiểm tra trích dẫn và giao diện là mã xử lý thông thường, **không phải AI tạo sinh**.

Tác động rõ nhất của AI là chuyển dữ liệu sách và cấu trúc lá số thành văn bản dễ đọc. Chưa có phép đo đủ để kết luận bài luận giải Gemini chính xác, an toàn hoặc được từng nguồn sách hỗ trợ. Chế độ **mock/bản mẫu** giúp kiểm thử và chạy khi thiếu khóa API, nhưng không phải kết quả AI.

## 2. AI được dùng ở đâu và tác động ra sao

| Phần hệ thống | AI hoặc kỹ thuật | Đầu vào → đầu ra | Tác động thực tế / dự kiến | Trạng thái và giới hạn |
|---|---|---|---|---|
| Hỏi đáp tri thức (`POST /api/v1/chat/ask`) | Gemini LLM qua `LLMProvider` | Câu hỏi + các đoạn sách đã truy xuất → câu trả lời tiếng Việt, tách theo sách | Người dùng đọc được bản tổng hợp thay vì tự dò từng đoạn; câu trả lời có số tham chiếu để tra lại nguồn. | Có mã gọi API thật; cần `GEMINI_API_KEY`. Khi không đủ ngữ cảnh, pipeline trả `insufficient_evidence`; khi lỗi Gemini trả `error`, không tự chuyển sang mock. Số trích dẫn được kiểm tra có tồn tại trong ngữ cảnh, **chưa chứng minh nội dung câu trả lời được nguồn hỗ trợ về ngữ nghĩa**. |
| Luận giải lá số (`POST /api/v1/horoscope/read`) | Gemini LLM với prompt và JSON đầu ra | Ngày/giờ sinh → lá số và đặc trưng → truy xuất đoạn sách → bài đọc về tổng quan, sự nghiệp, tài chính, tình cảm, đại hạn, gợi ý hành động | Biến thuật ngữ Tử Vi thành nội dung dễ hiểu cho người mới; tăng mức cá nhân hóa theo dữ liệu lá số. | Có tích hợp API và nhãn phân biệt Gemini với mock. Chưa nghiệm thu chất lượng Gemini thật trên bộ lá số đại diện; lời khuyên không được xem là dự báo khoa học hoặc tư vấn chuyên môn. |
| Tìm kiếm ngữ nghĩa cho KMS | Embedding cục bộ `BAAI/bge-m3` hoặc Gemini `gemini-embedding-001`, lưu Qdrant, kết hợp FTS5/RRF | Câu hỏi và chunk sách → vector → ứng viên nguồn | Có thể tìm các cách diễn đạt gần nghĩa mà từ khóa thuần túy bỏ sót; khả năng này cần so sánh với FTS trên cùng bộ đánh giá. | Adapter và script nạp chỉ mục đã có. Manifest hiện ghi **30 vector** và **4.350 chunk**; không thể coi dense index đã bao phủ toàn bộ kho. Mặc định cấu hình embedding là `local`; luồng horoscope hiện truy xuất **FTS5 trực tiếp**, không dùng embedding. |
| Bản mẫu và khả năng tiếp tục sử dụng | Bộ sinh văn bản theo quy tắc (`mock`) | Đặc trưng lá số → nội dung mẫu cố định | Cho phép chạy thử giao diện/API ngoại tuyến, giảm phụ thuộc dịch vụ ngoài khi demo và test. | **Không phải AI tạo sinh** và không tổng hợp nội dung theo các đoạn sách truy xuất. Horoscope tự chuyển sang mock nếu thiếu khóa hoặc gọi Gemini thất bại; giao diện hiển thị nguyên nhân. |

### Luồng dữ liệu và ranh giới trách nhiệm

1. **Dữ liệu nguồn:** Ba sách NPL, BD, DAU được đưa vào SQLite/FTS5; dữ liệu có thể còn lỗi OCR hoặc chưa duyệt thủ công.
2. **Tính toán lá số:** Thư viện `vendor/lasotuvi` và `horoscope_features.py` lập lá số, trích xuất sao/cung/đại hạn theo quy tắc. AI không tính hay xác minh lại lá số.
3. **Truy xuất:** `horoscope_rag_bridge.py` sinh câu tìm kiếm theo đặc trưng và lấy đoạn sách bằng FTS5; luồng hỏi đáp KMS dùng `Retriever` có thể phối hợp FTS và vector. Đây là bước chọn ngữ cảnh, không phải bằng chứng tự động cho mọi nhận định sau đó.
4. **Tạo văn bản:** Gemini chỉ nhận các đặc trưng/ngữ cảnh được ghép vào prompt để soạn câu trả lời. Với horoscope, nếu không có ngữ cảnh sách, prompt vẫn có thể tạo bài đọc từ đặc trưng lá số; cần tránh mô tả đầu ra đó là “đã được sách chứng minh”.
5. **Hiển thị:** Ứng dụng Streamlit trình bày bài đọc, lá số 12 cung và các đoạn nguồn đã truy xuất. Nguồn hiển thị là **ngữ cảnh đưa cho mô hình**, chưa phải xác nhận từng câu trong bài đọc có trích dẫn đúng.

Hai endpoint có phạm vi khác nhau: hỏi đáp KMS chặn yêu cầu dự đoán vận mệnh cá nhân; ứng dụng horoscope được thiết kế riêng để tạo bài đọc cá nhân mang tính tham khảo. Cần đánh giá an toàn cho luồng horoscope theo tiêu chí riêng.

## 3. Tác động có bằng chứng và điều chưa thể kết luận

| Nhận định | Bằng chứng hiện có | Kết luận hợp lệ |
|---|---|---|
| Giao diện có thể chạy từ nhập ngày sinh đến báo cáo | Nghiệm thu giai đoạn 5: `pytest tests/` **70 passed, 1 skipped**; kiểm tra trình duyệt với provider mock trên desktop/tablet/mobile, mở 12 cung và 10 nguồn trong ca thử. | Luồng kỹ thuật và hiển thị mock hoạt động trong điều kiện đã thử; **không** chứng minh chất lượng Gemini thật. |
| Truy xuất sách đã được đo trên tập hold-out | Báo cáo FTS-only 20 ca: Recall@5 **0,5882**, MRR **0,5**, cross-book leakage **0**, abstention accuracy **1,0**. | Đây là kết quả **FTS-only**, không phải điểm của AI ngôn ngữ hay embedding Gemini. Recall cho thấy vẫn bỏ sót nguồn ở một số câu. |
| Có nền tảng cho tìm kiếm vector | Manifest chỉ mục ghi model `gemini-embedding-001`, 30 vector, 4.350 chunk được xây dựng. | Chưa có cơ sở tuyên bố tìm kiếm ngữ nghĩa đã triển khai đầy đủ trên toàn bộ dữ liệu hoặc cải thiện recall so với FTS. |
| Bài luận giải AI an toàn và bám nguồn | Prompt có quy tắc tránh phán xét cực đoan; UI có thông báo chưa kiểm duyệt. Giai đoạn 6 vẫn chưa nghiệm thu. | Quy tắc trong prompt là biện pháp định hướng, **không phải bảo đảm**. Cần kiểm thử đầu ra Gemini thật và đối chiếu nguồn thủ công. |

**Không có số liệu hiện có** về thời gian tiết kiệm, độ hài lòng người dùng, chi phí API theo yêu cầu hoặc tỷ lệ chính xác của bài luận giải. Vì vậy báo cáo chỉ mô tả lợi ích chức năng và các phép đo thực sự có trong dự án.

## 4. Rủi ro, kiểm soát hiện có và việc cần làm

| Rủi ro/tác động bất lợi | Kiểm soát hiện có | Việc còn cần đánh giá |
|---|---|---|
| AI diễn đạt sai nội dung sách, bịa quan hệ nhân quả hoặc đưa lời khuyên quá chắc chắn | Prompt yêu cầu bám ngữ cảnh, tách theo sách; chat có ngưỡng từ chối khi thiếu chứng cứ và bộ kiểm số trích dẫn. | Đo groundedness/citation support trên Gemini thật, kiểm từng nhận định với đoạn sách; bổ sung bộ ca gây nhiễu và ca thiếu nguồn. |
| Dữ liệu nguồn OCR sai hoặc chưa được người duyệt | Metadata `trust_tier`, `verification_status=unverified`, nhãn “chưa kiểm duyệt” trên UI. | Kiểm mẫu theo trang PDF, sửa OCR, ghi trạng thái xác minh; không hiểu `trust_tier` là độ đúng của luận giải. |
| Nội dung cá nhân có thể gây lo âu hoặc ảnh hưởng quyết định về sức khỏe, tài chính, quan hệ | Prompt cấm phán xét cực đoan; footer nêu tính tham khảo; UI phân biệt mock/AI. | Hoàn thành giai đoạn 6: thử ít nhất các nhóm lá số biên và rà soát 100% mẫu nghiệm thu theo tiêu chí an toàn đã định; không dùng thay tư vấn chuyên môn. |
| Dữ liệu ngày giờ sinh được gửi đến nhà cung cấp AI khi chọn Gemini | Có chế độ mock không gọi Gemini; API chỉ gửi nội dung prompt cần thiết để tạo bài đọc. | Rà soát chính sách dữ liệu/quyền riêng tư, thông báo rõ cho người dùng trước khi triển khai công khai; không khẳng định thời hạn lưu giữ hoặc cơ chế xử lý của nhà cung cấp khi chưa kiểm chứng. |
| Phụ thuộc khóa API, mạng, giới hạn dịch vụ và chi phí | Horoscope fallback có nhãn; chat trả lỗi có trạng thái; mock hỗ trợ kiểm thử ngoại tuyến. | Đo độ trễ, lỗi và chi phí bằng cấu hình triển khai thật; đặt giới hạn/quota phù hợp. |

## 5. AI hỗ trợ quá trình phát triển dự án

Tài liệu `AGENTS.md` và `CLAUDE_TO_GEMINI_WORKFLOW.md` quy định/quảng bá quy trình dùng **Claude** để thiết kế ca kiểm thử và **Gemini** để triển khai theo TDD. Đây là **quy trình dự kiến trong tài liệu**; chỉ từ repository không thể xác nhận mức đóng góp thực tế của từng công cụ cho toàn bộ lịch sử mã nguồn.

Trong phạm vi giai đoạn 5 vừa thực hiện, **Codex** hỗ trợ đọc mã, viết giao diện và test; **Taste Skill** được dùng để định hướng và kiểm tra giao diện qua ảnh chụp trình duyệt. Tác động quan sát được là hoàn thành form, báo cáo, 12 cung, hiển thị nguồn và các ca kiểm thử được ghi ở mục 3. Kết quả `pytest` và kiểm tra trình duyệt là bằng chứng về hành vi phần mềm trong các ca đã chạy, không phải chứng nhận rằng mã do AI tạo ra không có lỗi.

Đối với các phần phát triển khác, muốn ghi nhận “AI viết bao nhiêu phần trăm mã” hoặc “tiết kiệm bao nhiêu giờ” cần nhật ký công việc và cách đo thống nhất; dự án hiện chưa có dữ liệu đó.

## 6. Kết luận

AI có vai trò **soạn văn bản trả lời và luận giải**, đồng thời có thể hỗ trợ **tìm kiếm ngữ nghĩa** trong luồng KMS. Giá trị đã thấy là đưa tri thức sách và cấu trúc lá số vào một giao diện dễ tiếp cận, có chế độ chạy thử không phụ thuộc API. Tác động về **độ đúng, mức bám nguồn, an toàn nội dung và lợi ích sử dụng thực tế** vẫn cần được đo bằng Gemini thật và đánh giá của con người trước khi công bố là đã đạt.

## Tài liệu đối chiếu trong repository

- Mã luồng hỏi đáp: [`backend/app/services/rag.py`](../backend/app/services/rag.py), [`backend/app/services/llm_provider.py`](../backend/app/services/llm_provider.py), [`backend/app/services/citation_validator.py`](../backend/app/services/citation_validator.py).
- Mã luận giải: [`backend/app/services/horoscope_features.py`](../backend/app/services/horoscope_features.py), [`backend/app/services/horoscope_rag_bridge.py`](../backend/app/services/horoscope_rag_bridge.py), [`backend/app/services/horoscope_interpreter.py`](../backend/app/services/horoscope_interpreter.py), [`backend/app/main.py`](../backend/app/main.py).
- Embedding/chỉ mục: [`backend/app/services/gemini_embeddings.py`](../backend/app/services/gemini_embeddings.py), [`backend/app/services/retriever.py`](../backend/app/services/retriever.py), [`data/processed/index_manifest.json`](../data/processed/index_manifest.json).
- Kết quả đánh giá và nghiệm thu: [`evaluations/results/eval_holdout_gate2.json`](../evaluations/results/eval_holdout_gate2.json), [`docs/HOROSCOPE_APP_CHECKLIST.md`](HOROSCOPE_APP_CHECKLIST.md), [`docs/HOROSCOPE_UI_DESIGN.md`](HOROSCOPE_UI_DESIGN.md), [`docs/RUN_HOROSCOPE.md`](RUN_HOROSCOPE.md).
- Quy trình dùng AI khi phát triển: [`AGENTS.md`](../AGENTS.md), [`docs/CLAUDE_TO_GEMINI_WORKFLOW.md`](CLAUDE_TO_GEMINI_WORKFLOW.md).

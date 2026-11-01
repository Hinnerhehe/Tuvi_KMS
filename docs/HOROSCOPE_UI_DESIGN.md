# Giai đoạn 5 — quyết định giao diện

## Hướng thiết kế

Áp dụng `design-taste-frontend` / Taste Skill, quy trình **app screens**.
Draw: `kind=report`, `screens=home,report`, light; chọn **Framed sheet**, seed **1621765852**.
Không redraw. Khung xanh xám nhẹ lấy từ sắc mực/ngọc, sheet trắng, màu nhấn `#1b6c80`.
IBM Plex Sans 400/500/600 được đóng gói tại chỗ, hỗ trợ tiếng Việt và chạy offline.

Câu hỏi chính: **Từ thông tin sinh, tôi có thể đọc hiểu gì về bản thân và đối chiếu ở đâu?**

Ý tưởng: **Bản đồ 12 cung trở thành mục lục trực quan cho một hồ sơ đọc có thể đối chiếu sách.**
Nhãn đời thường dẫn việc đọc; thuật ngữ, sao và nguồn cổ điển ở lớp chi tiết.
Biểu tượng ô cung và sơ đồ 12 địa chi được vẽ bằng mã; không sử dụng ảnh hay chứng thực giả.
Không có số đo tính cách, xác suất hay điểm số được tự tạo cho người dùng.

## Dữ liệu và tác vụ

- Hồ sơ: tên tùy chọn, ngày/tháng/năm, 12 khung giờ, lịch âm/dương, giới tính, năm xem.
- Tác vụ chính: gửi form một lần để tạo bài đọc.
- Báo cáo: định danh Mệnh/Cục/Mệnh cư/Thân cư, tổng quan, điểm mạnh, điều cần rèn luyện.
- Bốn chủ đề: sự nghiệp, tài chính, tình cảm, vận trình; các chủ đề chọn được đặt trước.
- Gợi ý hành động: đọc từ JSON hiện có, không thêm dữ liệu mẫu vào UI.
- Chi tiết: 12 cung JSON-safe, dùng chung renderer với `lasoban.py`.
- Nguồn: mã sách/chương/phần/trang từ database, đúng 500 ký tự được đưa vào prompt.
- Nguồn chưa duyệt được ghi rõ; không tuyên bố kiểm chứng ngữ nghĩa citation.
- Phân biệt provider yêu cầu với provider thực chạy và nguyên nhân chuyển sang mock.
- Trạng thái: chưa nhập, đang chờ, thành công, nguồn trống, sai ngày, lỗi mạng/timeout.
- Phiên báo cáo gắn với snapshot form lúc gửi, không thay đổi khi mở chi tiết.

## Kiểm tra và review hình ảnh

Kiểm thử tự động toàn bộ: **70 passed, 1 skipped**. Ca bỏ qua là smoke embedding dùng API thật.
Năm ca mới bao phủ hợp đồng API, nhãn fallback, lịch nhập, escape HTML, gửi form và
giữ kết quả qua các lần rerun/lỗi mạng.

Vòng đầu phát hiện font tải mạng, bóng drawer và menu che nội dung trên điện thoại.
Đã đóng gói font, bỏ bóng nặng và cho menu tự thu gọn. Review ảnh tiếp tục phát hiện
menu đã đóng vẫn giữ 310px trên tablet; sửa theo `data-collapsed` của Streamlit.

Các kiểm tra hình ảnh/tương tác cuối được ghi trong `.taste-skill/inspect-final/`
và `.taste-skill/report-ui/` khi chạy tại workspace. Đây là artifact QA, không phải mã sản phẩm.

Kết quả: màn hình ban đầu **0 FAIL / 0 WARN** qua inspector; màn hình báo cáo cũng
không có findings trong các probe/rule app của Taste Skill ở cả ba chiều rộng.
Chrome thực đã gửi form ở chế độ mock, chuyển sang tab tài chính, mở 12 cung và 10 nguồn;
không có JavaScript exception hay tràn ngang.

Review cuối theo bảy câu hỏi của app-screen workflow:

1. Tổng quan và thế mạnh dẫn việc đọc; không thêm biểu đồ hay điểm số tính cách giả.
2. Sheet và các khối dùng chung lề; menu đóng không giữ chỗ trên tablet; hai cột tổng quan
   nằm trên một bề mặt để không tạo hai thẻ kết thúc lệch nhau.
3. Màu nhấn ở sơ đồ, chính tinh và dữ liệu ngũ hành; khung trung tính, không gradient/bóng.
4. Snapshot ngày sinh/năm xem lấy từ cùng request; số nguồn khớp 10 nguồn trong response;
   đủ 12 ô cung. Không có tổng hay tỷ lệ tự tính cần đối soát thêm.
5. Thiếu dữ liệu hiện dấu gạch hoặc câu rỗng rõ nghĩa; không biến thiếu dữ liệu thành 0.
6. Không có biểu đồ định lượng/legend. Tên sao, phẩm cấp và ngũ hành có nhãn chữ, không
   dựa hoàn toàn vào màu; nguồn có sách và trang, không chỉ con số tham chiếu.
7. Điện thoại có nút Nhập ngày sinh, menu thu gọn, thống kê 2 cột, các cung thành danh sách;
   tab và công tắc hoạt động mà không tạo lại bài đọc.

Ngoại lệ: sidebar rộng 310px để chứa form có nhãn, thay vì 228px của bản draw.
Các biểu tượng menu/check và màu trạng thái mặc định của Streamlit được giữ lại;
không thêm ảnh hay nội dung minh họa cá nhân vào báo cáo thật.

Giới hạn: Giai đoạn 5 xác minh luồng UI với provider mock; chưa chứng nhận tính đúng đắn
của luận giải cá nhân, tính hỗ trợ ngữ nghĩa của nguồn hay chất lượng Gemini thật.
Các mục an toàn và kiểm thử thuật toán lịch biên của giai đoạn 6 vẫn cần nghiệm thu riêng.

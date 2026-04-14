# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Lê Trung Anh Quốc  
**Mã sinh viên:** 2A202600108  
**Vai trò:** Supervisor & Trace Owner, Worker, MCP Owner  

---

## 1. Phần tôi phụ trách
Trong dự án Lab Day 09, tôi chịu trách nhiệm thiết kế và hiện thực hóa kiến trúc điều phối trung tâm của hệ thống:
- **Thiết kế Supervisor Node (Tiered Keyword Dispatching):** Xây dựng logic rẽ nhánh dựa trên phân tích ý định người dùng với 3 tầng ưu tiên: Priority (P1, SLA), Policy Keywords và Error Keywords (`err-`). Logic này đảm bảo các tác vụ nguy cấp luôn được ưu tiên xử lý đúng worker.
- **Phát triển Worker Logic:** Trực tiếp xây dựng `synthesis.py` với bộ 5 quy tắc nghiêm ngặt (Strict Rules) để kiểm soát định dạng phản hồi (Kết quả, Giải thích, Căn cứ pháp lý). Tôi đã tối ưu hóa Prompt để đảm bảo trích dẫn nguồn chuẩn xác trong ngoặc vuông `[source.txt]`.
- **Cơ chế LLM-as-a-Judge khắt khe:** Cài đặt logic đánh giá kết quả dựa trên model `gpt-4o-mini` với bộ tiêu chí định lượng: trừ 0.2 điểm nếu thiếu citation, trừ 0.5 điểm nếu có dấu hiệu ảo giác (hallucination). Điều này giúp hệ thống đạt độ tin cậy trung bình **0.82** (tăng mạnh so với Day 08).
- **Thêm Smart HITL Route:** Tích hợp MCP server Brave Search vào `human_review_node` để cung cấp các gợi ý từ Internet cho chuyên gia, giúp xử lý các edge cases mà dữ liệu nội bộ không có.

## 2. Một quyết định kỹ thuật quan trọng
**Quyết định: Triển khai State-aware Routing và tách biệt Internet Research.**

**Lý do:** Thay vì một luồng RAG đơn giản, tôi chọn cách quản lý trạng thái qua mảng `workers_called`. Điều này cho phép Supervisor đưa ra quyết định dựa trên lịch sử hoạt động của agent. Quan trọng nhất, tôi quyết định cô lập việc tra cứu Internet chỉ dành cho nhánh `human_review` khi gặp mã lỗi lạ. Việc này giúp bảo vệ tính toàn vẹn của Knowledge Base nội bộ, tránh việc thông tin nhiễu từ mạng làm sai lệch các câu hỏi về quy định (SLA, Refund).

**Bằng chứng:** Trong file `graph.py`, logic điều hướng ưu tiên kiểm tra mã lỗi và trạng thái `hitl_triggered` trước khi quyết định kết thúc tại `synthesis`, đảm bảo mọi câu hỏi phức tạp đều đi qua đủ các bước cần thiết.

## 3. Một lỗi đã sửa
**Lỗi:** Supervisor nhận diện sai ý định khi người dùng hỏi về các mã lỗi kỹ thuật mới (như `ERR-403-AUTH`), dẫn đến việc hệ thống cố tra cứu trong tài liệu SLA/Policy và trả lời "Không tìm thấy thông tin".

**Cách sửa:** Tôi đã cập nhật bộ lọc Regex đặc hiệu trong Supervisor để đánh chặn các tiền tố `err-`. Khi phát hiện, hệ thống tự động kích hoạt Route `human_review`. Đồng thời, tôi tích hợp kết quả từ `web_search` để cung cấp thông tin sơ bộ ngay lập tức cho người dùng trong khi chờ chuyên gia phê duyệt.
**Lỗi:** Thiết kế luồng ban đầu bị sai, cả 2 route đều đi qua retrieval worker,sau khi tìm hiểu và đào sâu hơn về luồng hoạt động đúng của policy và retrieval worker, tôi đã sửa lại luồng hoạt động của hệ thống.
**Cách sửa:** Đổi logic route của supervisor, policy worker và retrieval worker.

**Kết quả:** Hệ thống hoạt động ổn định,latency giảm rõ rệt vì đã giảm tải throughput của retrieval worker. Toàn nhóm đạt kết quả tốt trong cả question cơ bản và grading question, xử lý mượt mà cả các trường hợp "bẫy" dữ liệu nhờ thêm route human review.

## 4. Tự đánh giá
- **Làm tốt:** Thiết kế luồng Graph chặt chẽ, cơ chế chấm điểm LLM-as-a-Judge hoạt động ổn định và có tính định lượng cao.
- **Yếu điểm:** Độ trễ (Latency) trung bình tăng lên ~14s do phải gọi LLM nhiều lần cho các bước Verify và Judge.
- **Phụ thuộc:** Nhóm phụ thuộc vào tôi trong việc duy trì tính đúng đắn của logic điều phối (Orchestration) và đảm bảo các Worker tuân thủ Contract chung của hệ thống.

## 5. Nếu có thêm 2h làm việc
Tôi sẽ nghiên cứu triển khai **Semantic Router** sử dụng Embeddings để thay thế cho bộ Keyword Matching hiện tại. Việc chuyển từ bắt từ khóa sang so sánh độ tương đồng về ngữ nghĩa sẽ giúp Supervisor phân loại Task chính xác hơn đối với các câu hỏi tự nhiên dài và phức tạp, từ đó giảm thiểu hoàn toàn sai sót trong điều hướng.

---
*File báo cáo cá nhân - Lab Day 09*

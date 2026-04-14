# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Lê Trung Anh Quốc  
**Mã sinh viên:** 2A202600108  
**Vai trò:** Supervisor & Trace Owner, Worker, MCP Owner  

---

## 1. Phần tôi phụ trách
Trong dự án Lab Day 09, tôi chịu trách nhiệm thiết kế và hiện thực hóa kiến trúc điều phối trung tâm của hệ thống:
- **Thiết kế Supervisor Node:** Xây dựng logic rẽ nhánh (Routing) dựa trên phân tích ý định người dùng, ưu tiên các tác vụ rủi ro cao hoặc cần ưu tiên (P1, Policy, SLA).
- **Phát triển Worker Logic:** Trực tiếp tham gia xây dựng `retrieval.py`, `policy_tool.py` và `synthesis.py`. Tôi đã tập trung vào việc đảm bảo Synthesis Worker có khả năng trích dẫn nguồn (Citation) chuẩn xác trong định dạng ngoặc vuông `[source.txt]`.
- **Cơ chế LLM-as-a-Judge:** Cài đặt logic đánh giá kết quả (Final Judge) dựa trên model gpt-4o-mini để đo lường độ tin cậy (Confidence) của câu trả lời trước khi trả về, giúp đáp ứng tiêu chí bonus của bài Lab.
- **Thêm human review route:** Thêm MCP server web search cho human review route để gợi ý, đề xuất hướng giải quyết cho các trường hợp đặc biệt.
## 2. Một quyết định kỹ thuật quan trọng
**Quyết định:** Triển khai thêm route human review để xử lý trường hợp đặc biệt
Quyết định tách retrieval thuần ra khỏi route của policy vì làm nghẽn perfomance, vi phạm cấu trúc của bài lab

**Lý do:** Các câu hỏi thực tế (như gq09) thường đòi hỏi kiến thức tổng hợp từ nhiều tài liệu khác nhau (Access Control và SLA). Nếu chỉ đi qua một worker rồi kết thúc, câu trả lời sẽ bị thiếu sót. Bằng cách cho phép Graph quay lại Supervisor sau mỗi bước (Cyclic), Supervisor có thể đưa ra quyết định gọi thêm worker phụ trợ nếu thấy thông tin chưa đủ, từ đó tối ưu hóa khả năng giải quyết các câu hỏi phức tạp (Multi-hop Reasoning).

**Bằng chứng:** Trong file `graph.py`, tôi đã triển khai mảng `workers_called` để Supervisor theo dõi lịch sử và quyết định liệu có cần tiếp tục "hop" sang worker tiếp theo hay chuyển sang bước `synthesis`.

## 3. Một lỗi đã sửa
**Lỗi:** Supervisor rẽ nhánh không chính xác khi gặp các câu hỏi có mã lỗi lạ (`ERR-xxx`), dẫn đến việc hệ thống cố gắng tìm trong Knowledge Base (thường là thất bại) thay vì escalate lên chuyên gia.

**Cách sửa:** Tôi đã cập nhật bộ lọc Regex trong Supervisor để ưu tiên nhận diện mã lỗi đặc thù. Nếu phát hiện `err-` trong câu hỏi, hệ thống sẽ tự động kích hoạt Route `human_review`. Đồng thời, tôi kết nối lộ trình này với cơ chế Internet Research để cung cấp thông tin sơ bộ ban đầu trước khi yêu cầu chuyên gia xác nhận.

**Kết quả:** Câu hỏi benchmark số 9 (`q09`) và grading question `gq07` đã được xử lý mượt mà, rẽ nhánh đúng vào quy trình Expert Review/Smart HITL thay vì trả lời sai.

## 4. Tự đánh giá
- **Làm tốt:** Khả năng thiết kế luồng Graph linh hoạt, xử lý được các trường hợp phức tạp và câu hỏi "bẫy".
- **Yếu điểm:** Việc quản lý State của Graph đôi khi hơi cồng kềnh, dẫn đến độ trễ (Latency) của hệ thống còn cao.
- **Phụ thuộc:** Nhóm phụ thuộc vào tôi ở việc đảm bảo tính đúng đắn của luồng điều hướng và chất lượng tổng hợp câu trả lời cuối cùng.

## 5. Nếu có thêm 2h làm việc
Tôi sẽ nghiên cứu triển khai **Semantic Router** sử dụng Embeddings để thay thế cho bộ Keyword Matching hiện tại. Việc chuyển từ bắt từ khóa sang so sánh độ tương đồng về ngữ nghĩa sẽ giúp Supervisor phân loại Task chính xác hơn đối với các câu hỏi tự nhiên, ít từ khóa đặc trưng, từ đó giảm thiểu sai sót trong điều hướng.

---
*File báo cáo cá nhân - Lab Day 09*

# Routing Decisions Log — Lab Day 09

**Nhóm:** Automata Tập Sự  
**Ngày:** 14/04/2026

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> SLA xử lý ticket P1 là bao lâu?

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `standard retrieval task`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** `retrieval_worker` -> `synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): Thông tin về SLA xử lý ticket P1 được lấy từ db nội bộ, phản hồi 15 phút, xử lý 4 giờ.
- confidence: `0.80`
- Correct routing? **Yes**

**Nhận xét:** 
Đây là câu hỏi truy vết thông tin dạng bảng biểu/FAQs thông thường nên đi vào Retrieval. Việc rẽ nhánh chính xác và lấy lại được Context giúp LLM cuối chặn được chính xác nguồn.

---

## Routing Decision #2

**Task đầu vào:**
> Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keyword | risk_high detected`  
**MCP tools được gọi:** `search_kb`, `get_ticket_info`  
**Workers called sequence:** `retrieval_worker`, `policy_tool_worker`, `synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): Bị từ chối hoặc cần sự kiện ngoại lệ khẩn cấp theo Policy. 
- confidence: `0.80`
- Correct routing? **Yes**

**Nhận xét:**
Hệ thống bắt gặp từ "cấp quyền Level 3", liền bẻ cung sang Policy Worker và MCP check. Việc này giúp Worker có định dạng kiểm tra luồng rủi ro, tuy nhiên logic trong Policy_Tool_Worker cần chuẩn hơn về phân rã "hoàn tiền" và "truy cập". 

---

## Routing Decision #3

**Task đầu vào:**
> ERR-403-AUTH là lỗi gì và cách xử lý?

**Worker được chọn:** `human_review` (chuyển qua `synthesis_worker` sau khi có context Internet)  
**Route reason (từ trace):** `unknown error code detected - needs expert review`  
**MCP tools được gọi:** `brave_search` (Internet lookup)  
**Workers called sequence:** `human_review` -> `synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): (Sau khi chuyên gia bấm Yes vào pop-up tìm kiếm Internet) Trả về lỗi 403 HTTP Forbidden.
- confidence: `0.80`
- Correct routing? **Yes**

**Nhận xét:**
Trường hợp mã lỗi dạng "ERR-XXX" không có sẵn trong CSDL sẽ được bẻ nhánh ra external Internet/Research, hoặc human review. Điều này hạn chế tối đa việc LLM tự bịa ra (hallucinate).

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 7 | 46% |
| policy_tool_worker | 7 | 46% |
| human_review/synthesis | 1 | 6% |

### Routing Accuracy

> Trong số 15 câu nhóm đã chạy, bao nhiêu câu supervisor route đúng?

- Câu route đúng: 15 / 15
- Câu route sai: 0
- Câu trigger HITL: 1 (Lỗi ERR-403-AUTH gọi manual prompt)

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?  

1. **Keyword Overriding**: Ưu tiên bắt keyword về chính sách (policy/access/refund) làm rule thượng tầng trước khi check cẩn thận.
2. Dùng keyword "ERR-" làm cờ kích hoạt chức năng tra cứu web ngoài, tránh ảo giác LLM cho lỗi ko tồn tại trong DB nội bộ. Hệ thống sẽ có Live Web Search thông minh như một fallback rất tốt.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  

Rất tốt và hữu ích. Các lý do rẽ nhánh dạng chuỗi tag string (ví dụ: `task contains policy/access keyword | chọn MCP | risk_high detected`) giúp nhà thiết kế nhận ra ngay luồng kiểm tra `if-else` nào hoạt động ở đoạn code Supervisor.

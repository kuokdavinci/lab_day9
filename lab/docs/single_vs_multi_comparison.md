
---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | ~0.70 | 0.82 | +0.12 | Hệ thống tự tin hơn nhờ dùng Judge đánh giá chéo. |
| Avg latency (ms) | ~3,500 | 11,457 | +7,957 | Multi-agent chạy tuần tự nhiều worker và lookup external tool. |
| Abstain rate (%) | ~12% | ~6% | -6% | Khả năng tự tin hơn khi bí (Web Search) thay vì ngô nghê chối. |
| Multi-hop accuracy | Dưới 70% | 100% (15/15 success)| N/A | Pass toàn bộ test plan Day 09. |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | Trace file log cực kì chi tiết minh bạch. |
| Debug time (estimate) | 20 phút | 5 phút | -15 phút| Cô lập vấn đề theo từng Agent rất nhanh. |

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Tương đối tốt | Rất tốt (100%) |
| Latency | Rất nhanh (<4s) | Khá nhanh (~6s-8s) |
| Observation | Kết quả retrieve (top-k chunks + score) được sử dụng trực tiếp, không có bước kiểm tra hay refine. | Kết quả retrieval được phân tích (relevance, thiếu thông tin, conflict) để quyết định bước tiếp theo (rewrite query, retrieve lại, chọn source khác) |

**Kết luận:** Multi-agent RAG không mang lại cải thiện đáng kể về độ chính xác đối với các truy vấn đơn giản, rủi ro thấp, nơi mà single-pass retrieval đã đủ hiệu quả. Tuy nhiên, kiến trúc này giúp chuẩn hóa đầu ra thông qua việc phân tách vai trò và kiểm soát định dạng. Đổi lại, latency tăng lên do chi phí điều phối và nhiều bước suy luận (multi-step inference), không chỉ riêng overhead từ Supervisor.
Trong các bài toán phức tạp hoặc thiếu thông tin, multi-agent thể hiện lợi thế rõ rệt khi có khả năng lặp, đánh giá và điều chỉnh truy xuất, từ đó cải thiện độ chính xác tổng thể.


---

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 (Single / Naive RAG) | Day 09 (Multi-Agent / Orchestrated RAG) |
|---------|-----------------------------|----------------------------------------|
| Accuracy | Thấp khi query cần multi-hop hoặc cross-domain | Cao hơn nhờ tách bước và xử lý theo từng nguồn |
| Routing visible? | ✗ (LLM tự suy đoán, không kiểm soát) | ✓ (routing rõ ràng qua agent / tool) |
| Observation | Kết quả retrieval thô, không được kiểm soát → dễ trộn lẫn policy và data | Observation được phân tách theo từng nguồn và dùng để điều phối hành động tiếp theo |
| Data handling | Trộn lẫn unstructured (policy) và structured (DB/API) trong 1 bước | Tách riêng: policy (retriever) vs data (DB/API tool) |
| Failure mode | Hallucination, context mixing | Fail có kiểm soát (sai ở bước nào rõ ràng) |
| Use case fit | Query đơn giản, low-risk | Query phức tạp: multi-hop, cross-system, cần check nhiều điều kiện |
| Latency | Thấp (single-pass) | Cao hơn (multi-step + orchestration overhead) |

---

### 2.3 Câu hỏi cần abstain (thiếu/không có thông tin)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | 1/15 | Sử dụng MCP và gợi ý có Human Review |
| Hallucination cases | Ít | Ít |


**Kết luận:**
Nhờ Worker Synthesis, các câu hỏi ambiguous sẽ bị gạt bỏ bằng mức confidence = 0.0 để đẩy cờ HITL (nhờ người can thiệp).

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: 20-30 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc file trace json → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing heuristics.
  → Nếu retrieval sai → test retrieval_worker.py độc lập.
  → Nếu synthesis sai → test sysnthesis.py với fixed input.
Thời gian ước tính: 3-5 phút
```

**Câu cụ thể nhóm đã debug:** _(Mô tả 1 lần debug thực tế trong lab)_
Ở Task `Cần cấp quyền Level 3 để khắc phục P1...`, Supervisor route đúng vào Policy, nhưng final answer lại đi nói chuyện "Hoàn tiền". Khi xem trace, nhìn được ngay list exceptions là "hoàn tiền không áp dụng". Chỉ cần vào nhánh `policy_tool_worker.py` sửa lại cái Rule kiểm tra Keyword hoàn tiền/cấp quyền. Cô lập bug hoàn toàn.

---

## 4. Extensibility Analysis

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa khối Chain/Prompt gốc | Khai báo trong thư viện MCP `mcp_server.py`. |
| Thêm 1 domain mới | Retrain prompt lớn | Thêm 1 worker mới (VD: HR_Worker). |
| Thay đổi retrieval strategy | Sửa module lõi | Chỉ Sửa `retrieval.py` độc lập. |
| A/B test một phần | Khó — Phải duplicate file | Dễ — Switch cờ Supervisor đụng trúng Worker V2. |

**Nhận xét:**
Kiến trúc Microservice hóa quy trình prompt giúp hệ thống Agent dễ dàng bảo trì và mở rộng. 

---

## 5. Cost & Latency Trade-off

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 1-2 LLM calls (LLM judge) |
| Complex query | 1 LLM call (dễ tạch) | 2-3 LLM calls (Judge, Policy) |
| MCP tool call | Không có | Tùy tool (có web search) |


---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. Khả năng **Cách ly rủi ro / Quản lý Bug**: Pipeline hỏng đoạn nào biết ngay đoạn đó do JSON trace lưu IO của từng sub-worker riêng rẽ.
2. Khả năng **Xử lý linh hoạt**: Có thể bypass context, gọi các API hệ thống đặc thù thông qua MCP mà không làm nhiễu loạn những tác vụ trả lời căn bản thông thường (Retrieval).

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. Tiêu hao Latency (gấp đôi gấp ba thời gian xoay trục) và API token cost tăng vọt từ các LLM "Judge".

> **Khi nào KHÔNG nên dùng multi-agent?**

Khi triển khai các hệ thống Q&A "trò chuyện phím" nhỏ nhặt, FAQ đơn giản tĩnh, hoặc dự án không cho phép chi tiêu API vượt mức.

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

Làm Router bằng LLM nhẹ thay vì if/else cứng (Zero-shot Router), và phát triển MCP client real để các Agent "nhắn tin" được trên Slack/Jira.
Nếu được, sẽ scale hệ thống chạy concurency để handle được nhiều request cùng lúc, giảm latency xuống mức chấp nhận được.
